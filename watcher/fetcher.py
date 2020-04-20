import json
import logging
import os.path
from typing import List, Tuple

from sgqlc.endpoint.http import HTTPEndpoint
from sgqlc.operation import Operation

from .schema import Commit
from .schema import github_schema as schema, GitActor, User

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(message)s", level=logging.INFO)


class QueryError(Exception):
    pass


class GithubDataFetcher:
    def __init__(self, repo_owner, repo_name, branch, gh_token):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self._client = self._get_gql_client(gh_token)

    @staticmethod
    def _get_gql_client(gh_token) -> HTTPEndpoint:
        headers = {"Authorization": f"bearer {gh_token}"}
        client = HTTPEndpoint(
            url="https://api.github.com/graphql", base_headers=headers
        )
        return client

    def _get_response(self, query: Operation, request_uuid: str, force=False):
        # Read from file cache if the same request already made, otherwise make a request
        # to github API
        response_cached_file = f"./watcher/response_cache/{request_uuid}.json"
        if os.path.isfile(response_cached_file) and not force:
            logger.info("Loading response from cache")

            with open(response_cached_file, "r") as f:
                response = json.load(f)
                return response

        logger.info("Getting response from API:")
        logger.info(query)
        response = self._client(query)
        if "errors" in response:
            raise QueryError(response["errors"])

        with open(response_cached_file, "w") as f:
            json.dump(response, f)

        return response

    def _filter_commits_and_prs(
        self, commits: List[Commit], from_sha: str, to_sha: str
    ) -> Tuple[List[Commit], bool]:
        # There should be a way to get this filtering done in GraphQL query, but
        # commits are in order from latest to earliest, so we need to start tracking
        # commits once we see 'to_sha' and continue until we get to 'from_sha'
        filtered_commits = []
        start = False
        for commit in commits:
            if commit.oid == to_sha:
                start = True
            if not start:
                continue
            commit.associated_pull_requests.nodes = [
                pr
                for pr in commit.associated_pull_requests.nodes
                if pr.base_ref_name == self.branch
            ]
            if commit.oid == from_sha:
                return filtered_commits, True
            filtered_commits.append(commit)
        return filtered_commits, False

    def get_commit_history(self, from_sha: str, to_sha: str) -> List[Commit]:
        request_uuid = (
            f"commit-history:{self.repo_owner}-{self.repo_name}-{self.branch}"
            f"-{from_sha}-{to_sha}"
        )

        query = Operation(schema.Query)
        commits = (
            query.repository(owner=self.repo_owner, name=self.repo_name)
            .object(expression=self.branch)
            .__as__(Commit)
            .history(first=100)
            .nodes
        )
        commits.__fields__("id", "oid", "message", "changed_files")
        commits.author.__as__(GitActor).name()

        prs = commits.associated_pull_requests(first=5).nodes
        prs.__fields__("id", "number", "url", "merged_at", "base_ref_name")
        prs.merged_by.__as__(User).name()
        prs.author.__as__(User).name()
        pr_commits = prs.commits(first=100)
        pr_commits.__fields__("total_count")
        pr_commits.nodes.commit.__fields__("oid", "url")

        files = prs.files(first=100)
        files.__fields__("total_count")
        files.nodes.__fields__("path", "additions", "deletions")

        response = self._get_response(query, request_uuid)
        commits_all = (query + response).repository.object.history.nodes
        result, finished = self._filter_commits_and_prs(commits_all, from_sha, to_sha)

        return result
