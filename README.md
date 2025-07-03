# git-archive-zip-bug-trailer-contains-additional-0x06054b50

This program reproduces a subtle bug in `git archive --format=zip` when `trailer` contains an additional instance of the signature value `0x06054b50`.
https://github.com/git/git/blob/v2.49.0/archive-zip.c#L588-L603 .
The result is that the output `.zip` file is corrupted and cannot be read by most unzipping programs.

This is accomplished by creating a git commit with a large number of files that have very long names such that `trailer.size` aka "size of the central directory" is exactly `0x06054b50`.
In principle, this bug could also be reproduced with the field `trailer.offset` aka "offset of start of central directory with respect to the starting disk number",
or by the bytes appearing spanned across multiple fields, such as the last byte of `trailer.entries` and the first three bytes of `trailer.size`.

`git archive --format=zip` is vulnerable to this bug because it includes an archive comment in the output zip file (with a length greater than `3`).
APPNOTE.txt, the official ZIP format spec, does not forbid the signature from appearing in the "end of central directory record" after the "signature" before 22 bytes prior to the end of the file,
which means the ZIP file format is ambiguous.
Most unzipping programs scan backward for the signature and trust the occurrence closest to the end of the file,
which means that most unzipping programs will identify what `git` intended to be the "size of the central directory" as the "signature",
and the desync causes the rest of the parsing to fail catastrophically.
A sufficiently sophisticated hacker could in principle create a git commit that when downloaded/exported as a ZIP file appears to unzip correctly with surprising contents.

Interestingly, while many ZIP implementations note in code comments that the archive comment must not contain the signature,
no implementation that I could find noticed that the signature ambiguity can also happen in the rest of the "end of central directory record" fields.
This is evidence that this bug is especially subtle and nefarious.
Examples: https://github.com/python/cpython/blob/3.14/Lib/zipfile/__init__.py#L366-L367 , https://github.com/thejoshwolfe/yazl/blob/3.3.1/index.js#L159 .

GitHub uses `git archive --format=zip` for the "Download ZIP" button in the "Code" dropdown,
which means you can reproduce this bug by clicking that button here (as of 2025 June):
TODO link to the result.

## Usage

```bash
git version  # reproduced of 2.49.0

./cause-problems.py --output /some/path.zip

unzip -l /some/path.zip  # results in an error
```
