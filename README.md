# poc-github-zip-exploit

This program generates a git commit that when downloaded from GitHub using the Download ZIP button results in a corrupt ZIP file.
We manage to get the size of the central directory field to be the exact signature of the end of central directory record thereby throwing off the search for the signature during initial load of a ZIP file.
This only causes a problem because the generated ZIP file includes a comment that has length at least 12 bytes.
GitHub is almost certainly using `git archive --format=zip`, which always includes the 40-character commit sha1 in hex.
ZIP file comments are generally dangerous to include in ZIP files for this reason.

The result on GitHub is here:
https://github.com/thejoshwolfe/poc-github-zip-exploit/tree/b65497e8a662866aaf6d68dc59608ebb620982db

You can also run this program locally to reproduce the problem offline:

```
./cause-problems.py --output /some/path.zip
unzip -l /some/path.zip
```
