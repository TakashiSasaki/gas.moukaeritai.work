# Google Apps Script Project Management

This repository is used to download all projects from Google Apps Script and manage them using Git.

このリポジトリは複数のGoogle Apps Scriptプロジェクトを集めてコードを一元管理するためのものです。各 GAS プロジェクトは `projects/` 配下に配置されています。
各サブディレクトリ名は Google Apps Script の Script ID をそのまま使っています。

## Purpose

The primary purpose of this repository is to provide a centralized location for:

*   **Backing up** your Google Apps Script projects.
*   **Version controlling** your scripts, allowing you to track changes, revert to previous versions, and collaborate more effectively.
*   **Managing** multiple Google Apps Script projects within a single Git repository structure.

## How it Works (General Idea)

Typically, this setup involves using a tool like `clasp` (the command-line tool for Google Apps Script) or custom scripts to:

1.  **List** all your Google Apps Script projects.
2.  **Clone** or **pull** each project into `projects/<SCRIPT_ID>/`.
3.  **Commit** changes to Git to keep a history of your script development.

This allows you to leverage the power of Git for your Google Apps Script development workflow.

## GitHub Actions Workflows

This repository utilizes GitHub Actions workflows to automate certain tasks. These workflows now operate on the default branch, `gas.moukaeritai.work`.

### Sync from GAS

*   **Trigger:** Manual dispatch or downstream `workflow_run`.
*   **Purpose:** Automatically pulls the latest code from all registered Google Apps Script projects.
*   **Process:**
    1.  Checks out the `gas.moukaeritai.work` branch.
    2.  Uses `clasp` to pull updates for each linked Google Apps Script project into `projects/<SCRIPT_ID>/`.
    3.  If any changes are detected, commits them to the default branch with the message "chore: sync GAS projects".

### Update Apps Script Projects List

*   **Trigger:** Manual dispatch.
*   **Purpose:** Keeps an updated list of all Google Apps Script projects associated with the account.
*   **Process:**
    1.  Checks out the `gas.moukaeritai.work` branch.
    2.  Uses `clasp list` to fetch the current list of projects.
    3.  Saves this list to the `clasp-list.txt` file.
    4.  If the `clasp-list.txt` file has changed since the last run, commits the updated file to the default branch with the message "Update Apps Script projects list and JSON".

These workflows help ensure that the repository remains a current backup and version-controlled representation of your Google Apps Script projects.
