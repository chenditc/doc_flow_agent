# Developer Certificate of Origin (DCO)

This project uses the Developer Certificate of Origin (DCO) to ensure that all contributions are properly licensed and that contributors have the legal right to make their contributions.

## What is the DCO?

The Developer Certificate of Origin (DCO) is a lightweight way for contributors to certify that they wrote or otherwise have the right to submit the code they are contributing to the project.

## DCO Text

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I have the right to submit it under the open source license indicated in the file; or

(b) The contribution is based upon previous work that, to the best of my knowledge, is covered under an appropriate open source license and I have the right under that license to submit that work with modifications, whether created in whole or in part by me, under the same open source license (unless I am permitted to submit under a different license), as indicated in the file; or

(c) The contribution was provided directly to me by some other person who certified (a), (b) or (c) and I have not modified it.

(d) I understand and agree that this project and the contribution are public and that a record of the contribution (including all personal information I submit with it, including my sign-off) is maintained indefinitely and may be redistributed consistent with this project or the open source license(s) involved.

## How to Sign Your Work

To sign your work, just add a line like this at the end of your commit message:

```
Signed-off-by: Random J Developer <random@developer.example.org>
```

This can be easily done using the `-s` flag when committing:

```bash
git commit -s -m "Add awesome new feature"
```

You can also configure Git to automatically sign off all your commits:

```bash
git config --global format.signoff true
```

## DCO Enforcement

All commits must be signed off. Commits that are not signed off will be rejected by our automated checks.

If you forget to sign off a commit, you can amend it:

```bash
git commit --amend -s
```

For multiple commits, you can rebase and sign off each commit:

```bash
git rebase --signoff HEAD~<number-of-commits>
```

## Questions?

If you have questions about the DCO process, please open an issue or contact the maintainers.
