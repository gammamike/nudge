//! Per-user installation with owned paths, managed Bash setup, and atomic activation.

use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt, symlink};
use std::path::{Component, Path, PathBuf};

use anyhow::{Context, Result, bail, ensure};
use serde::{Deserialize, Serialize};
use tempfile::{Builder, NamedTempFile};

use crate::paths;

const HOOK: &str = include_str!("../nudge.bash");
const LICENSE: &str = include_str!("../LICENSE");
const BEGIN: &str = "# >>> nudge managed setup >>>";
const END: &str = "# <<< nudge managed setup <<<";

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct State {
    format: u32,
    bin_dir: PathBuf,
    bashrc: Option<PathBuf>,
}

struct Lock(PathBuf);

impl Drop for Lock {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

fn path_text(path: &Path) -> Result<&str> {
    let text = path
        .to_str()
        .context("installation paths must be valid UTF-8")?;
    ensure!(
        path.is_absolute() && !text.chars().any(char::is_control),
        "installation paths must be absolute and contain no control characters"
    );
    ensure!(
        !path.components().any(|c| c == Component::ParentDir),
        "installation paths must not contain '..'"
    );
    Ok(text)
}

fn exists(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok()
}

fn regular(path: &Path) -> Result<()> {
    ensure!(
        fs::symlink_metadata(path)?.file_type().is_file(),
        "expected a regular file, not a symlink: {}",
        path.display()
    );
    Ok(())
}

fn owned_directory(path: &Path) -> Result<()> {
    ensure!(
        fs::symlink_metadata(path)?.file_type().is_dir(),
        "expected a directory, not a symlink: {}",
        path.display()
    );
    Ok(())
}

fn lock(root: &Path) -> Result<Lock> {
    let path = root.join(".lock");
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(&path)
        .context(
            "installation is locked; if no Nudge installer is running, remove its stale .lock file",
        )?;
    writeln!(file, "{}", std::process::id())?;
    Ok(Lock(path))
}

fn read_state(root: &Path) -> Result<State> {
    owned_directory(root)?;
    regular(&root.join("install.json"))?;
    let state: State = serde_json::from_slice(&fs::read(root.join("install.json"))?)?;
    ensure!(state.format == 1, "unsupported installation format");
    ensure!(
        !path_text(&state.bin_dir)?.contains(':'),
        "binary directory cannot contain ':'"
    );
    if let Some(path) = &state.bashrc {
        path_text(path)?;
    }
    Ok(state)
}

fn save_state(root: &Path, state: &State) -> Result<()> {
    let mut file = NamedTempFile::new_in(root)?;
    serde_json::to_writer_pretty(&mut file, state)?;
    writeln!(file)?;
    file.as_file().sync_all()?;
    file.persist(root.join("install.json"))?;
    Ok(())
}

fn installed_root(executable: &Path) -> Option<PathBuf> {
    let bin = executable.parent()?;
    let release = bin.parent()?;
    let releases = release.parent()?;
    (bin.file_name()? == "bin" && releases.file_name()? == "releases")
        .then(|| releases.parent().map(Path::to_path_buf))
        .flatten()
        .filter(|root| root.join("install.json").is_file())
}

fn target(root: &Path, name: &str) -> Result<Option<PathBuf>> {
    let link = root.join(name);
    if !exists(&link) {
        return Ok(None);
    }
    let target = fs::read_link(&link)
        .with_context(|| format!("{} must be an owned symlink", link.display()))?;
    let parts: Vec<_> = target.components().collect();
    ensure!(
        parts.len() == 2
            && parts[0] == Component::Normal("releases".as_ref())
            && matches!(parts[1], Component::Normal(name) if name.to_str().is_some_and(|s| s.starts_with("release-"))),
        "invalid installation link: {}",
        link.display()
    );
    owned_directory(&root.join(&target))?;
    regular(&root.join(&target).join("bin/nudge"))?;
    regular(&root.join(&target).join("nudge.bash"))?;
    Ok(Some(target))
}

fn set_link(root: &Path, name: &str, value: &Path) -> Result<()> {
    let temporary = Builder::new().prefix(".link-").tempdir_in(root)?;
    let link = temporary.path().join("new");
    symlink(value, &link)?;
    fs::rename(&link, root.join(name))?;
    Ok(())
}

fn quote(value: &str) -> String {
    format!("'{}'", value.replace('\'', "'\\''"))
}

fn copy_notices(source: &Path, destination: &Path) -> Result<()> {
    if !exists(source) {
        return Ok(());
    }
    let kind = fs::symlink_metadata(source)?.file_type();
    if kind.is_dir() {
        fs::create_dir(destination)?;
        for item in fs::read_dir(source)? {
            let item = item?;
            copy_notices(&item.path(), &destination.join(item.file_name()))?;
        }
    } else {
        ensure!(
            kind.is_file(),
            "license notices must be regular files or directories"
        );
        fs::copy(source, destination)?;
    }
    Ok(())
}

fn block(root: &Path, bin_dir: &Path) -> Result<String> {
    let bin = quote(path_text(bin_dir)?);
    let hook = quote(path_text(&root.join("current/nudge.bash"))?);
    Ok(format!(
        "\n{BEGIN}\ncase \":$PATH:\" in\n    *:{bin}:*) ;;\n    *) export PATH={bin}:\"$PATH\" ;;\nesac\nif [[ -r {hook} ]]; then\n    source {hook}\nfi\n{END}\n"
    ))
}

struct ShellEdit {
    path: PathBuf,
    original: String,
    temporary: NamedTempFile,
    backup: Option<PathBuf>,
}

impl ShellEdit {
    fn prepare(path: &Path, body: &str, install: bool) -> Result<Option<Self>> {
        let original = if exists(path) {
            regular(path).context("Bash startup file is not a regular file; use --no-modify-shell and configure sourcing manually")?;
            fs::read_to_string(path)?
        } else {
            String::new()
        };
        let has_markers = original.contains(BEGIN) || original.contains(END);
        if has_markers {
            ensure!(
                original.matches(BEGIN).count() == 1
                    && original.matches(END).count() == 1
                    && original.matches(body).count() == 1,
                "managed Bash block was edited or belongs to another installation; resolve it manually before continuing"
            );
        }
        let outside = if has_markers {
            original.replacen(body, "", 1)
        } else {
            original.clone()
        };
        if install {
            ensure!(
                !outside.contains("nudge.bash"),
                "remove the existing manual nudge.bash source block before installing, or use --no-modify-shell"
            );
        }
        let next = if install && has_markers {
            original.clone()
        } else if install {
            format!("{outside}{body}")
        } else {
            outside
        };
        if next == original {
            return Ok(None);
        }
        let parent = path
            .parent()
            .context("startup file needs a parent directory")?;
        ensure!(
            parent.is_dir(),
            "startup-file directory does not exist: {}",
            parent.display()
        );
        let mut temporary = NamedTempFile::new_in(parent)?;
        temporary.write_all(next.as_bytes())?;
        let permissions = if exists(path) {
            fs::metadata(path)?.permissions()
        } else {
            fs::Permissions::from_mode(0o600)
        };
        temporary.as_file().set_permissions(permissions.clone())?;
        temporary.as_file().sync_all()?;
        let backup = if exists(path) {
            let prefix = format!(
                "{}.nudge-backup-",
                path.file_name()
                    .context("startup filename missing")?
                    .to_string_lossy()
            );
            let mut backup = Builder::new().prefix(&prefix).tempfile_in(parent)?;
            backup.write_all(original.as_bytes())?;
            backup.as_file().set_permissions(permissions)?;
            backup.as_file().sync_all()?;
            Some(backup.keep()?.1)
        } else {
            None
        };
        Ok(Some(Self {
            path: path.to_owned(),
            original,
            temporary,
            backup,
        }))
    }

    fn apply(self) -> Result<()> {
        if exists(&self.path) {
            regular(&self.path)?;
            ensure!(
                fs::read_to_string(&self.path)? == self.original,
                "startup file changed during installation; retry after reviewing it"
            );
        } else {
            ensure!(
                self.backup.is_none(),
                "startup file was removed during installation"
            );
        }
        self.temporary.persist(&self.path)?;
        if let Some(backup) = self.backup {
            println!("Startup-file backup: {}", backup.display());
        }
        Ok(())
    }
}

fn activate(root: &Path, next: &Path, current: Option<&Path>) -> Result<()> {
    if let Some(current) = current {
        set_link(root, "previous", current)?;
    }
    set_link(root, "current", next)?;
    File::open(root)?.sync_all()?;
    Ok(())
}

pub(crate) fn execute(action: &str, arguments: Vec<String>) -> Result<()> {
    let mut prefix = None;
    let mut bashrc = None;
    let mut modify_shell = true;
    let mut args = arguments.into_iter();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--prefix" => {
                prefix = Some(PathBuf::from(args.next().context("missing --prefix path")?))
            }
            "--bashrc" if action == "install" => {
                bashrc = Some(PathBuf::from(args.next().context("missing --bashrc path")?))
            }
            "--no-modify-shell" if action == "install" => modify_shell = false,
            "--help" | "-h" => {
                println!(
                    "nudge {action} [--prefix ABSOLUTE_PATH]\ninstall: [--bashrc ABSOLUTE_PATH] [--no-modify-shell]\nDefault: ~/.local/bin and $XDG_DATA_HOME/nudge (or ~/.local/share/nudge).\nSettings and caches are preserved by uninstall. Rollback selects the previous installed release."
                );
                return Ok(());
            }
            _ => bail!("unknown {action} option: {arg}"),
        }
    }
    ensure!(
        modify_shell || bashrc.is_none(),
        "--bashrc and --no-modify-shell cannot be combined"
    );
    let executable = env::current_exe()?;
    let (root, bin_dir) = if let Some(prefix) = prefix {
        path_text(&prefix)?;
        (prefix.join("share/nudge"), prefix.join("bin"))
    } else if let Some(root) = installed_root(&executable) {
        let state = read_state(&root)?;
        (root, state.bin_dir)
    } else {
        (
            paths::xdg("XDG_DATA_HOME", ".local/share")?.join("nudge"),
            paths::home()?.join(".local/bin"),
        )
    };
    path_text(&root)?;
    ensure!(
        !path_text(&bin_dir)?.contains(':'),
        "binary directory cannot contain ':'"
    );
    if let Some(path) = &bashrc {
        path_text(path)?;
    }
    if !exists(&root) && action == "uninstall" {
        println!("Nudge is not installed at {}", root.display());
        return Ok(());
    }
    if action != "install" {
        ensure!(
            exists(&root),
            "Nudge is not installed at {}",
            root.display()
        );
    }
    let existing = if exists(&root) {
        Some(read_state(&root).context("refusing an unmanaged or invalid installation directory")?)
    } else {
        None
    };
    if let Some(state) = &existing {
        ensure!(
            state.bin_dir == bin_dir,
            "installed binary directory does not match requested location"
        );
    }
    let link = bin_dir.join("nudge");
    let destination = root.join("current/bin/nudge");
    if action == "install" && exists(&link) {
        ensure!(
            fs::read_link(&link).ok().as_deref() == Some(&destination),
            "refusing to replace an unrelated executable: {}",
            link.display()
        );
    }
    let rc = if action == "install" && modify_shell {
        let wanted =
            match bashrc.or_else(|| existing.as_ref().and_then(|state| state.bashrc.clone())) {
                Some(path) => path,
                None => paths::home()?.join(".bashrc"),
            };
        if let Some(previous) = existing.as_ref().and_then(|state| state.bashrc.as_ref()) {
            ensure!(
                *previous == wanted,
                "startup-file location cannot be changed without uninstalling first"
            );
        }
        Some(wanted)
    } else {
        existing.as_ref().and_then(|state| state.bashrc.clone())
    };
    let body = block(&root, &bin_dir)?;
    let edit = if action != "rollback" && (action == "uninstall" || modify_shell) {
        rc.as_ref()
            .map(|rc| ShellEdit::prepare(rc, &body, action == "install"))
            .transpose()?
            .flatten()
    } else {
        None
    };
    if !exists(&root) {
        fs::create_dir_all(&root)?;
        save_state(
            &root,
            &State {
                format: 1,
                bin_dir: bin_dir.clone(),
                bashrc: None,
            },
        )?;
    }
    let _guard = lock(&root)?;
    let releases = root.join("releases");
    if exists(&releases) {
        owned_directory(&releases)?;
    } else if action == "install" {
        fs::create_dir(&releases)?;
    }
    let current = target(&root, "current")?;
    let previous = target(&root, "previous")?;
    match action {
        "install" => {
            let source = fs::read(&executable)?;
            let unchanged = current.as_ref().is_some_and(|path| {
                fs::read(root.join(path).join("bin/nudge")).ok().as_ref() == Some(&source)
                    && fs::read_to_string(root.join(path).join("nudge.bash"))
                        .ok()
                        .as_deref()
                        == Some(HOOK)
            });
            let next = if unchanged {
                current
                    .clone()
                    .expect("unchanged installation has a current release")
            } else {
                let staging = Builder::new().prefix("release-").tempdir_in(&releases)?;
                fs::create_dir(staging.path().join("bin"))?;
                let binary = staging.path().join("bin/nudge");
                let mut file = OpenOptions::new()
                    .write(true)
                    .create_new(true)
                    .mode(0o755)
                    .open(binary)?;
                file.write_all(&source)?;
                file.sync_all()?;
                fs::write(staging.path().join("nudge.bash"), HOOK)?;
                fs::write(staging.path().join("LICENSE"), LICENSE)?;
                if let Some(bundle) = executable
                    .parent()
                    .filter(|parent| parent.file_name().is_some_and(|name| name == "bin"))
                    .and_then(Path::parent)
                {
                    for name in ["THIRD_PARTY_NOTICES.md", "licenses"] {
                        copy_notices(&bundle.join(name), &staging.path().join(name))?;
                    }
                }
                let path = staging.keep();
                PathBuf::from("releases")
                    .join(path.file_name().context("release directory missing")?)
            };
            fs::create_dir_all(&bin_dir)?;
            if !exists(&link) {
                symlink(&destination, &link)?;
            }
            save_state(
                &root,
                &State {
                    format: 1,
                    bin_dir,
                    bashrc: rc,
                },
            )?;
            if let Some(edit) = edit {
                edit.apply()?;
            }
            if !unchanged {
                activate(&root, &next, current.as_deref())?;
            }
            println!(
                "Installed nudge {} at {}",
                env!("CARGO_PKG_VERSION"),
                link.display()
            );
            if modify_shell {
                println!("Open a new Bash shell or run exec bash to load the installation.");
            } else {
                println!(
                    "Source {} in interactive Bash to enable corrections.",
                    quote(path_text(&root.join("current/nudge.bash"))?)
                );
            }
        }
        "rollback" => {
            let previous = previous.context("no previous installation is available")?;
            ensure!(
                current.as_ref() != Some(&previous),
                "no different previous installation is available"
            );
            activate(&root, &previous, current.as_deref())?;
            println!("Rolled back Nudge. Start a new Bash shell to reload its hook.");
        }
        "uninstall" => {
            for item in fs::read_dir(&root)? {
                let name = item?.file_name();
                ensure!(
                    ["install.json", "releases", "current", "previous", ".lock"]
                        .iter()
                        .any(|s| name == *s),
                    "unexpected file in installation; refusing removal: {}",
                    name.to_string_lossy()
                );
            }
            if let Some(edit) = edit {
                edit.apply()?;
            }
            if fs::read_link(&link).ok().as_deref() == Some(&destination) {
                fs::remove_file(&link)?;
            }
            fs::remove_dir_all(&root)?;
            println!(
                "Nudge uninstalled. Configuration, cache, and startup-file backups were preserved. Start a new Bash shell."
            );
        }
        _ => unreachable!(),
    }
    Ok(())
}
