//! Bounded subprocesses with process-group cleanup and no shell evaluation.

use std::io::{Read, Seek, SeekFrom};
use std::os::unix::process::CommandExt;
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::{Duration, Instant};

use anyhow::{Result, bail};
use rustix::process::{self, Pid, Signal};

pub(crate) struct Output {
    pub status: ExitStatus,
    pub stdout: String,
    pub stderr: String,
}

pub(crate) struct Runner {
    pub interrupted: Arc<AtomicBool>,
}

struct ChildGuard {
    child: Child,
    finished: bool,
}

impl Drop for ChildGuard {
    fn drop(&mut self) {
        if !self.finished {
            if let Some(pid) = Pid::from_raw(self.child.id() as i32) {
                let _ = process::kill_process_group(pid, Signal::KILL);
            }
            let _ = self.child.wait();
        }
    }
}

impl Runner {
    pub fn check_interrupt(&self) -> Result<()> {
        if self.interrupted.load(Ordering::Relaxed) {
            bail!("interrupted");
        }
        Ok(())
    }

    pub fn run(&self, command: &mut Command, timeout: Duration) -> Result<Output> {
        self.check_interrupt()?;
        // Files avoid pipe-buffer deadlocks without introducing reader threads.
        let mut stdout = tempfile::tempfile()?;
        let mut stderr = tempfile::tempfile()?;
        command
            .process_group(0)
            .stdout(stdout.try_clone()?)
            .stderr(stderr.try_clone()?);
        let mut guard = ChildGuard {
            child: command.spawn()?,
            finished: false,
        };
        let started = Instant::now();
        let status = loop {
            self.check_interrupt()?;
            if let Some(status) = guard.child.try_wait()? {
                guard.finished = true;
                break status;
            }
            if started.elapsed() >= timeout {
                bail!("subprocess timed out after {:.1}s", timeout.as_secs_f64());
            }
            thread::sleep(Duration::from_millis(2));
        };
        stdout.seek(SeekFrom::Start(0))?;
        stderr.seek(SeekFrom::Start(0))?;
        let mut out = String::new();
        let mut err = String::new();
        stdout.read_to_string(&mut out)?;
        stderr.read_to_string(&mut err)?;
        Ok(Output {
            status,
            stdout: out,
            stderr: err,
        })
    }

    pub fn capture(&self, executable: &str, args: &[&str]) -> Result<String> {
        let result = self.run(
            Command::new(executable).args(args).stdin(Stdio::null()),
            Duration::from_secs(5),
        )?;
        if !result.status.success() {
            bail!("command discovery failed");
        }
        Ok(result.stdout)
    }
}
