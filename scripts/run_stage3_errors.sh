#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
check_error() {
    vfs_path=$1
    if output=$(printf '%s\n' 'ls' 'exit' | \
        "$project_dir/run.sh" --vfs-path "$vfs_path" 2>&1); then
        echo 'Ожидалась ошибка загрузки VFS.' >&2
        exit 1
    fi
    printf '%s\n' "$output"
}

check_error "$project_dir/examples/missing-vfs.xml"
check_error "$project_dir/examples/vfs_invalid.xml"
