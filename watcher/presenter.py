from typing import Dict, List

from watcher.schema import Commit


class HistoryPresenter:
    def __init__(self, commits: List[Commit]):
        self.commits = commits

    def _aggregate_commits(self) -> Dict:

        prs = []
        authors = set()

        for commit in self.commits:
            for pr in commit.associated_pull_requests.nodes:
                prs.append(pr)

                authors.add(pr.author.name)

        prs_unique = list(set(prs))
        return {"prs_unique": prs_unique, "authors": authors}

    def print_commit_history(self, details=True) -> None:

        commit_aggregate = self._aggregate_commits()
        authors = commit_aggregate["authors"]
        print(f"Diff made by {len(authors)} different authors")

        prs_unique = commit_aggregate["prs_unique"]
        print(f"Diff contained {len(prs_unique)} Pull Requests")
        if not details:
            return

        prs_sorted = sorted(prs_unique, key=lambda x: x.merged_at)
        for pr in prs_sorted:
            print(
                f"PR#{pr.number} author: {pr.author.name}, merged by: {pr.merged_by.name}"
            )
            commits = ", ".join([prc.commit.oid for prc in pr.commits.nodes])
            print(f"\t Commits: {pr.commits.total_count} - {commits}")

            print(f"\t Changing {pr.files.total_count} files")
            for file in pr.files.nodes:
                print(f"\t\t{file.path} +{file.additions} -{file.deletions}")
            print(pr.url)
