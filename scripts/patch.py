#!/usr/bin/env python3
"""Narrow, fail-closed MailCraft source adaptation; no generic AppData manipulation.

The portable marker is the exact App/MailCraft/portable.txt, *and* a compiled
MailCraftPortable.exe at the package root. Both MailCraft binaries use it.
"""
import argparse
from pathlib import Path

HELPER = '''/// PortableApps-only data directory. Recognition requires the exact package layout
/// and a marker beside the binary, not a mutable current working directory.
/// Windows Credential Manager must not be used in this mode.
pub fn portable_data() -> Option<PathBuf> {
    if !cfg!(windows) { return None; }
    let exe = std::env::current_exe().ok()?;
    let app_dir = exe.parent()?;
    if !app_dir.file_name()?.to_string_lossy().eq_ignore_ascii_case("MailCraft") { return None; }
    let app_parent = app_dir.parent()?;
    if !app_parent.file_name()?.to_string_lossy().eq_ignore_ascii_case("App") { return None; }
    let root = app_parent.parent()?;
    if !app_dir.join("portable.txt").is_file() || !root.join("MailCraftPortable.exe").is_file() {
        return None;
    }
    Some(root.join("Data").join("MailCraft"))
}
'''


def replace_exact(path, old, new):
    original = path.read_text(encoding='utf-8')
    if original.count(old) != 1:
        raise RuntimeError(f'Source drift: {path} expected exactly one patch anchor, saw {original.count(old)}. Refusing unsafe build.')
    path.write_text(original.replace(old, new), encoding='utf-8', newline='\n')


def patch(root):
    control = root / 'crates/control-key/src/lib.rs'
    opened = root / 'apps/mailcraft/src/opened_files.rs'
    secrets = root / 'apps/mailcraft/src/secrets.rs'
    if not all(p.is_file() for p in (control, opened, secrets)):
        raise RuntimeError('MailCraft source files missing or upstream layout changed')
    replace_exact(control,
        'pub fn settings_dir() -> Option<PathBuf> {\n    if cfg!(target_os = "macos") {',
        HELPER + '\npub fn settings_dir() -> Option<PathBuf> {\n    if let Some(dir) = portable_data() { return Some(dir); }\n    if cfg!(target_os = "macos") {')
    replace_exact(opened,
        'pub fn base() -> Option<PathBuf> {\n    let cache = if cfg!(windows) {',
        'pub fn base() -> Option<PathBuf> {\n    if let Some(data) = mailcraft_control_key::portable_data() {\n        return Some(data.join("Attachments"));\n    }\n    let cache = if cfg!(windows) {')
    replace_exact(secrets,
        'pub fn store() -> Option<std::sync::Arc<dyn SecretStore>> {\n    #[cfg(any(target_os',
        'pub fn store() -> Option<std::sync::Arc<dyn SecretStore>> {\n    // Prevent persisted portable-account secrets in the host Windows Credential Manager.\n    if mailcraft_control_key::portable_data().is_some() { return None; }\n    #[cfg(any(target_os')
    print('SOURCE-ADAPTED: MailCraft settings/attachments/credential handling; fail-closed source anchors confirmed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    patch(args.source)
