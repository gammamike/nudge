//! Single-key confirmation with terminal restoration on cancellation/errors.

use std::fs::{File, OpenOptions};
use std::io::{self, Read, Write};

use anyhow::Result;
use rustix::event::{self, PollFd, PollFlags, Timespec};
use rustix::io::Errno;
use rustix::termios::{
    self, LocalModes, OptionalActions, QueueSelector, SpecialCodeIndex, Termios,
};

use crate::ai::Provider;
use crate::engine::Suggestion;
use crate::process::Runner;

struct TerminalGuard {
    file: File,
    original: Termios,
}

impl Drop for TerminalGuard {
    fn drop(&mut self) {
        let _ = termios::tcsetattr(&self.file, OptionalActions::Drain, &self.original);
    }
}

fn readable(file: &File, milliseconds: i64) -> Result<bool> {
    let mut descriptors = [PollFd::new(file, PollFlags::IN)];
    let timeout = Timespec {
        tv_sec: milliseconds / 1000,
        tv_nsec: milliseconds % 1000 * 1_000_000,
    };
    match event::poll(&mut descriptors, Some(&timeout)) {
        Ok(count) => Ok(count > 0),
        Err(Errno::INTR) => Ok(false),
        Err(error) => Err(error.into()),
    }
}

pub(crate) fn announce(provider: Provider) -> Result<()> {
    writeln!(
        OpenOptions::new().write(true).open("/dev/tty")?,
        "nudge: checking with {}… (Ctrl+C cancels)",
        provider.label()
    )?;
    Ok(())
}

pub(crate) fn confirm(result: &Suggestion, runner: &Runner) -> Result<()> {
    let Some(suggestion) = &result.suggestion else {
        if matches!(
            result.source.as_str(),
            "codex" | "claude" | "ollama" | "local-llm"
        ) {
            writeln!(
                OpenOptions::new().write(true).open("/dev/tty")?,
                "nudge: {}",
                result.reason.as_deref().unwrap_or("no suggestion")
            )?;
        }
        return Ok(());
    };
    let file = OpenOptions::new().read(true).write(true).open("/dev/tty")?;
    let original = termios::tcgetattr(&file)?;
    let mut guard = TerminalGuard { file, original };
    let mut settings = guard.original.clone();
    settings
        .local_modes
        .remove(LocalModes::ICANON | LocalModes::ECHO);
    settings.special_codes[SpecialCodeIndex::VMIN] = 1;
    settings.special_codes[SpecialCodeIndex::VTIME] = 0;
    termios::tcsetattr(&guard.file, OptionalActions::Flush, &settings)?;
    termios::tcflush(&guard.file, QueueSelector::IFlush)?;
    write!(
        guard.file,
        "\nnudge [{}, {:.0} ms]: {}\nEnter to run · Any other key to cancel ",
        result.source, result.elapsed_ms, suggestion
    )?;
    let mut key = [0];
    loop {
        runner.check_interrupt()?;
        if readable(&guard.file, 50)? {
            guard.file.read_exact(&mut key)?;
            break;
        }
    }
    if !matches!(key[0], b'\r' | b'\n') {
        if key[0] == 0x1b {
            let mut rest = [0; 64];
            while readable(&guard.file, 30)? {
                if guard.file.read(&mut rest)? == 0 {
                    break;
                }
            }
        }
        writeln!(guard.file, "\nCancelled.")?;
        return Ok(());
    }
    writeln!(guard.file)?;
    drop(guard);
    if let (Some(executable), Some(argv)) = (&result.executable, &result.argv) {
        let mut stdout = io::stdout().lock();
        for word in std::iter::once(executable).chain(argv.iter().skip(1)) {
            stdout.write_all(word.as_bytes())?;
            stdout.write_all(&[0])?;
        }
    }
    Ok(())
}
