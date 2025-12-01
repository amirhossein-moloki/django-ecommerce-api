# Contributing to Hypex E-commerce API

First off, thank you for considering contributing to the Hypex E-commerce API! It's people like you that make this project such a great tool.

## Where do I go from here?

If you've noticed a bug or have a feature request, [make one](https://github.com/m-h-s/E-commerce-api/issues/new)! It's generally best if you get confirmation of your bug or approval for your feature request this way before starting to code.

### Fork & create a branch

If this is something you think you can fix, then [fork the repo](https://github.com/m-h-s/E-commerce-api/fork) and create a branch with a descriptive name.

A good branch name would be (where issue #38 is the ticket you're working on):

```bash
git checkout -b 38-add-a-bigger-button
```

### Get the test suite running

Make sure you're running the test suite locally before you start making changes.

```bash
docker-compose exec web pytest
```

### Implement your fix or feature

At this point, you're ready to make your changes! Feel free to ask for help; everyone is a beginner at first :smile_cat:

### Make a Pull Request

At this point, you should switch back to your master branch and make sure it's up to date with the latest upstream version of the code.

```bash
git remote add upstream git@github.com:m-h-s/E-commerce-api.git
git checkout master
git pull upstream master
```

Then update your feature branch from your local copy of master, and push it!

```bash
git checkout 38-add-a-bigger-button
git rebase master
git push --force-with-lease origin 38-add-a-bigger-button
```

Finally, go to GitHub and [make a Pull Request](https://github.com/m-h-s/E-commerce-api/compare)

### Keeping your Pull Request updated

If a maintainer asks you to "rebase" your PR, they're saying that a lot of code has changed, and that you need to update your branch so it's easier to merge.

To learn more about rebasing and merging, check out [this guide](https://www.atlassian.com/git/tutorials/merging-vs-rebasing).

Once you've updated your branch, you'll need to force push the changes to your remote branch.

```bash
git push --force-with-lease origin 38-add-a-bigger-button
```
