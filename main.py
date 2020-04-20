import click

from watcher.fetcher import GithubDataFetcher
from watcher.presenter import HistoryPresenter


@click.command(
    help="Diff sumarize", context_settings={"help_option_names": ["--help", "-h"]},
)
@click.option(
    "--repo-owner", "-o", help="Owner of the repo",
)
@click.option(
    "--repo-name", "-r", help="Repo name",
)
@click.option(
    "--branch", "-b", default="master", help="Branch to track",
)
@click.option(
    "--token", "-t", help="Github access token",
)
@click.option(
    "--start-sha", "-s", help="Start analysis at sha",
)
@click.option(
    "--end-sha", "-e", help="End analysis at sha",
)
def main(repo_owner, repo_name, branch, token, start_sha, end_sha):

    data_fetcher = GithubDataFetcher(
        repo_owner=repo_owner, repo_name=repo_name, branch=branch, gh_token=token
    )

    commits = data_fetcher.get_commit_history(from_sha=start_sha, to_sha=end_sha)
    presenter = HistoryPresenter(commits)
    presenter.print_commit_history()


if __name__ == "__main__":
    main()
