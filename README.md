# git-archive-zip-bug-trailer-contains-additional-0x06054b50

This program reproduces a subtle bug in `git archive --format=zip` when `trailer` contains an additional instance of the signature value `0x06054b50`.
https://github.com/git/git/blob/v2.49.0/archive-zip.c#L588-L603 .
The result is that the output `.zip` file is corrupted and cannot be read by most unzipping programs.

GitHub appears to use `git archive --format=zip` for the "Download ZIP" button in the "Code" dropdown,
which means you can reproduce this bug by clicking that button here (as of 2025 June):
https://github.com/thejoshwolfe/git-archive-zip-bug-trailer-contains-additional-0x06054b50/tree/d3def4cc51e39c8a1c4270b1c22a3b53c7027cae

This bug is reproduced by creating a git commit with a large number of files that have very long names such that `trailer.size` aka "size of the central directory" is exactly `0x06054b50`.
In principle, this bug could also be reproduced with the field `trailer.offset` aka "offset of start of central directory with respect to the starting disk number",
or by the bytes spanning across multiple fields, such as the last byte of `trailer.entries` and the first three bytes of `trailer.size`.

`git archive --format=zip` is vulnerable to this bug because it includes an archive comment in the output zip file (with a length greater than `3`).
APPNOTE.txt, the official ZIP format spec, does not forbid the signature from appearing in the "end of central directory record" after the "signature" before 22 bytes prior to the end of the file,
which means the ZIP file format is ambiguous.
Most unzipping programs scan backward for the signature and trust the occurrence closest to the end of the file,
which means that most unzipping programs will identify what `git` intended to be the "size of the central directory" as the "signature",
and the desync causes the rest of the parsing to fail catastrophically.
A sufficiently sophisticated hacker could in principle create a git commit that when downloaded/exported as a ZIP file appears to unzip correctly with surprising contents.

Interestingly, while many ZIP implementations seem aware that the archive comment must not contain the signature,
no implementation that I could find seemed aware that the signature ambiguity can also happen in the rest of the fields of the "end of central directory record".
Examples: https://github.com/python/cpython/blob/3.14/Lib/zipfile/__init__.py#L366-L367 , https://github.com/thejoshwolfe/yazl/blob/3.3.1/index.js#L159 , Info-ZIP 3.0 `zipfile.c:scanzipf_regnew():L3492`.
It is counterintuitive that adding a comment introduces ambiguity in seemingly unrelated fields earlier in the struct.
Because git never includes the signature in the archive comment itself, the git developers could have had a false sense of confidence including an archive comment,
falling for the same misunderstanding as the developers of the above linked projects.
However this is speculation, as there is no relevant commentary I could find in the code or commit messages all the way back to the feature's initial introduction in https://github.com/git/git/commit/e4fbbfe9eccd37c0f9c060eac181ce05988db76c .

## Usage

```bash
git version  # reproduced with 2.49.0

./cause-problems.py --output /some/path.zip

unzip -l /some/path.zip  # results in an error
```

As of UnZip 6.00, prints this error:
```
Archive:  /some/path.zip
dea086f3a12af410e3fc0f491b4c
caution:  zipfile comment truncated
warning [/some/path.zip]:  zipfile claims to be last disk of a multi-part archive;
  attempting to process anyway, assuming all parts have been concatenated
  together in order.  Expect "errors" and warnings...true multi-part support
  doesn't exist yet (coming soon).
error [/some/path.zip]:  missing 2428817731 bytes in zipfile
  (attempting to process anyway)
error [/some/path.zip]:  attempt to seek before beginning of zipfile
  (please check that you have transferred or created the zipfile in the
  appropriate BINARY mode and that you have compiled UnZip properly)
```
