# OdysseyDecomp Progress Tracking

This repo is used as an issue tracker and claiming system for [OdysseyDecomp](https://github.com/MonsterDruide1/OdysseyDecomp). Visit the [issues](https://github.com/MonsterDruide1/OdysseyDecompTracker/issues) and [project board](https://github.com/users/MonsterDruide1/projects/1).

## Workflow

1. Pick a class you want to decompile, or ask for someone to suggest something on our [Discord](https://discord.gg/u2dfaQpDh5).
2. Search for the corresponding issue to check its current progress and difficulty. Keep in mind that GitHub's search cannot find words from the middle of a word, so make sure you include the start of the filename. Make sure it's not assigned to anyone else so far. Check the comments so far to see if anyone already did some work on it.
3. If you're happy with taking it, comment `/claim` to assign yourself to the issue.
4. Decompile the file you've picked according to the [Contribution Guide](https://github.com/MonsterDruide1/OdysseyDecomp/blob/master/Contributing.md).
5. Create a PR on `OdysseyDecomp` to add your code into the repo. Reference the issue from this repo in the description.
6. Once it's merged, the issue will be closed automatically!

If you're stuck with something on the file:
- Ask for help on our [Discord](https://discord.gg/u2dfaQpDh5) server.
- If it cannot be solved quick enough, add the `help wanted` label to your issue by commenting `/help`
- If you want to stop working on it for a while and eventually plan to come back, add the `/stale` label
- If you give up on the file, use `/unclaim` to remove your assignment. Add a comment with all information that could be helpful for the next person taking on this file, possibly link to your unfinished branch (make sure you don't delete it later though!) or attach some code snippets to explain the situation or provide a head start.

## List of commands

Command    | Alias     | Effect
-----------|-----------|--------
/claim     | /assign   | Assign the issue to yourself
/unclaim   | /unassign | Remove your assignment from the issue
/help      |           | Add https://github.com/MonsterDruide1/OdysseyDecompTracker/labels/help%20wanted label
/unhelp    | /thanks   | Remove https://github.com/MonsterDruide1/OdysseyDecompTracker/labels/help%20wanted label
/stale     |           | Add https://github.com/MonsterDruide1/OdysseyDecompTracker/labels/stale label
/unhelp    |           | Remove https://github.com/MonsterDruide1/OdysseyDecompTracker/labels/stale label
/request   |           | Add https://github.com/MonsterDruide1/OdysseyDecompTracker/labels/requested label
/unrequest |           | Remove https://github.com/MonsterDruide1/OdysseyDecompTracker/labels/requested label

## Future Ideas
- add command to allow linking WIP branch that shows up in issue body, not only in comment below
    - as GitHub application, authenticate as user, then create new branch based on existing one, delete original, then "create linked branch" to the old name, finally delete temporary branch
- labels for "parts" of the game (at least separating al from rs)
- auto-claim and link PRs being created on `OdysseyDecomp`
- do not mark issues auto-closed due to the file being deleted as "Done", but fully remove them from the project board instead
