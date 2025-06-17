from github import Github, Auth
from enum import Enum
import cxxfilt
import os, requests

DRY_RUN = True
OWNER = "MonsterDruide1"
REPO = "OdysseyDecompTracker"
FINE_TOKEN = os.getenv("FINE_TOKEN")
PROJECT_TOKEN = os.getenv("PROJECT_TOKEN")

PROJECT_ID = "PVT_kwHOAZIPJM4AxQt0"
STATUS_ID = "PVTSSF_lAHOAZIPJM4AxQt0zgnZrEM"
STATUS_TODO_ID = "f75ad846"
STATUS_INPROGRESS_ID = "47fc9ee4"
STATUS_DONE_ID = "98236657"

SPLIT_BODY_METADATA = "\n\n---\n<!--START OF METADATA-->\n"

class FunctionStatus(Enum):
    Matching = 0
    NonMatchingMinor = 1
    NonMatchingMajor = 2
    NotDecompiled = 3
    Wip = 4
    Library = 5

class Function:
    def __init__(self, offset: int, status: FunctionStatus, size: int, name: str, lazy: bool):
        self.offset = offset
        self.status = status
        self.size = size
        self.name = name
        self.lazy = lazy
    
    def get_issue_line(self):
        try:
            name = self.name
            if name.endswith("_0"):
                name = name[:-2]
            demangled_name = cxxfilt.demangle(name)
            if demangled_name == "''":
                demangled_name = ""
            if demangled_name != "":
                demangled_name = "`" + demangled_name + "`"
        except Exception as e:
            print(f"Failed to demangle {self.name}: {e}")
            demangled_name = self.name + " (demangle failed)"
        return f"| " +\
               f"{'⬜' if self.status == FunctionStatus.NotDecompiled else '✅'}" +\
               f" | `0x71{self.offset:08X}` | {demangled_name}{' (lazy)' if self.lazy else ''} | {self.size}" +\
               f" |"

class File:
    # functions: dict[offset: int, tuple[status: FunctionStatus, size: int, mangled: str]]
    def __init__(self, name: str, functions: list[Function]):
        self.name = name
        self.functions = functions

    def is_implemented(self):
        return all(f.status != FunctionStatus.NotDecompiled for f in self.functions)

    def issue_body(self):
        issue_lines = "\n".join([f.get_issue_line() for f in self.functions]);
        return f"""\
The following functions should be listed in this object:
| status | address | function | size (bytes) |
| :----: | :------ | :------- | :----------- |
{issue_lines}
        """

    def get_total_size(self):
        return sum(f.size for f in self.functions)

    def get_total_functions(self):
        return len(self.functions)

    def difficulty(self):
        # 0    < X < 500  : Easy (blue - 0-20%)
        # 500  < X < 1500 : Normal (green - 20-50 = 30%)
        # 1500 < X < 5000 : Hard (orange - 50-80% = 30%)
        # 5000 < X < 10000: Harder (red - 80-92 = 12%)
        # 10000 < X       : Insane (purple, 92-100 = 8%)
        total_size = self.get_total_size()
        if total_size < 500:
            return "easy"
        elif total_size < 1500:
            return "normal"
        elif total_size < 5000:
            return "hard"
        elif total_size < 10000:
            return "harder"
        else:
            return "insane"

    def project(self):
        if self.name.startswith("Project/") or self.name.startswith("Library/") or self.name.startswith("Unknown/"):
            return "al"
        elif self.name.startswith("agl/"):
            return "agl"
        elif self.name.startswith("sead"):
            return "sead"
        elif self.name.startswith("nn/"):
            return "nn"
        elif self.name.startswith("eui/"):
            return "eui"
        else:
            return "game"


def truncate(text, length, appendix):
    appendix_length = len(appendix)
    if len(text) + appendix_length > length:
        text = text[:(length - appendix_length)]
        # delete until last newline
        text = text[:text.rfind("\n")]
        text += "\n... (truncated)"
    return text + appendix

def parse_file_list(file_list_lines: list[str]) -> dict[str, File]:
    files = {}
    current_object_name = ""
    current_functions = []
    current_offset = 0
    current_size = 0
    current_label = ""
    for i, line in enumerate(file_list_lines):
        line = line.strip()
        if line.endswith(".o:") or line.endswith("UNKNOWN:"):
            if len(current_functions) > 0:
                files[current_object_name] = File(current_object_name, current_functions)
                current_functions = []
            current_object_name = line.strip(":")
        if "offset:" in line:
            current_offset = int(line.split(" ")[-1], 16)
        if "size:" in line:
            current_size = int(line.split(" ")[-1])
        elif "label:" in line:
            # Get first element if label is a string array
            if "-" in file_list_lines[i + 1]:
                current_label = file_list_lines[i + 1].split(" ")[-1].strip()
            else:
                current_label = line.split(" ")[-1]
        elif "status:" in line:
            status_str = line.split(" ")[-1]
            status = FunctionStatus[status_str]
            lazy = "lazy: true" in file_list_lines[i + 1]
            current_functions.append(Function(current_offset, status, current_size, current_label, lazy))

    if len(current_functions) > 0:
        files[current_object_name] = File(current_object_name, current_functions)
        current_functions = []
    return files

print("Loading file list...")
file_list = {}
with open('data/file_list.yml', 'r') as f:
    file_list = parse_file_list(list(f))

# Limit to first 8 files for testing
#file_list = {k: file_list[k] for k in list(file_list)[:20]}

auth = Auth.Token(FINE_TOKEN)
g = Github(auth=auth)

repo = g.get_repo(OWNER+"/"+REPO)
label_unmanaged = repo.get_label("unmanaged")
label_implement = repo.get_label("implement")

print("Iterating and adjusting issues...")
files_handled = set()
for issue in repo.get_issues(state="open"):
    if label_unmanaged in issue.labels:
        continue

    if issue.title.startswith("Implement "):
        file_name = issue.title.split("Implement ")[1]
        if file_name not in file_list:
            print(f"Deleting issue: {issue.title}")
            if not DRY_RUN:
                issue.create_comment(body="File has been removed from the file list.")
                issue.edit(state="closed")
            continue
        file = file_list[file_name]
        if file.is_implemented():
            files_handled.add(file_name)
            print(f"Deleting issue: {issue.title}")
            if not DRY_RUN:
                issue.create_comment(body="File has been implemented.")
                issue.edit(state="closed")

        target_body = file_list[file_name].issue_body()
        current_body = issue.body
        current_metadata_requests = []
        if SPLIT_BODY_METADATA in current_body:
            current_body, metadata = current_body.split(SPLIT_BODY_METADATA, 1)
            for line in metadata.split("\n"):
                if line == "":
                    continue
                if "This file has been requested by " in line:
                    if current_metadata_requests != []:
                        print("Multiple metadata requests found, ignoring")
                        continue
                    list_of_people = line.split("This file has been requested by ")[1].split(", ")
                    for person in list_of_people:
                        if person.startswith("@"):
                            current_metadata_requests.append(person)
                        else:
                            print(f"Found request metadata, but person is not in mention format: {person}")
                else:
                    print(f"Unknown metadata line: {line}")

        target_metadata_requests = list(current_metadata_requests)
        comments = issue.get_comments()
        if issue.comments > 0:
            for comment in comments:
                if comment.body == "/request":
                    if comment.user.login not in target_metadata_requests:
                        target_metadata_requests.append("@"+comment.user.login)
                        print(f"Adding {comment.user.login} to metadata requests")
                    else:
                        print(f"{comment.user.login} is already in metadata requests")
                    
                    if not DRY_RUN:
                        comment.delete()
                elif comment.body == "/unrequest":
                    if "@"+comment.user.login in target_metadata_requests:
                        target_metadata_requests.remove("@"+comment.user.login)
                        print(f"Removing {comment.user.login} from metadata requests")
                    else:
                        print(f"{comment.user.login} is not in metadata requests")
                        
                    if not DRY_RUN:
                        comment.delete()
        
        target_metadata = []
        if len(target_metadata_requests) > 0:
            target_metadata.append("This file has been requested by " + ", ".join(target_metadata_requests))

        metadata = ""
        if len(target_metadata) > 0:
            metadata = "\n\n---\n<!--START OF METADATA-->\n" + "\n".join(target_metadata) + "\n"

        target_body = truncate(target_body, 65500, metadata)

        if issue.body != target_body:
            print(f"Updating issue: {issue.title}")
            print(f"Current body: {current_body}")
            print(f"Target body: {target_body}")
            if not DRY_RUN:
                issue.edit(body=target_body)
        
        target_requested = len(target_metadata_requests) > 0
        current_requested = "requested" in [lab.name for lab in issue.labels]
        if target_requested != current_requested:
            print(f"Updating issue requested: {issue.title} -> {target_requested}")
            if not DRY_RUN:
                if target_requested:
                    issue.add_to_labels("requested")
                else:
                    issue.remove_from_labels("requested")

        target_difficulty = "difficulty:"+file_list[file_name].difficulty()
        current_difficulties = [lab.name for lab in issue.labels if lab.name.startswith("difficulty:")]
        if target_difficulty not in current_difficulties or len(current_difficulties) > 1:
            print(f"Updating issue difficulty: {issue.title} -> {target_difficulty}")
            if not DRY_RUN:
                for lab in current_difficulties:
                    issue.remove_from_labels(lab)
                issue.add_to_labels(target_difficulty)
        
        target_good_first_issue = file_list[file_name].get_total_size() < 100
        current_good_first_issues = "good first issue" in [lab.name for lab in issue.labels]
        if target_good_first_issue != current_good_first_issues:
            print(f"Updating issue good first issue: {issue.title} -> {target_good_first_issue}")
            if not DRY_RUN:
                if target_good_first_issue:
                    issue.add_to_labels("good first issue")
                else:
                    issue.remove_from_labels("good first issue")

        target_project = "project:"+file_list[file_name].project()
        current_projects = [lab.name for lab in issue.labels if lab.name.startswith("project:")]
        if target_project not in current_projects or len(current_projects) > 1:
            print(f"Updating issue project: {issue.title} -> {target_project}")
            if not DRY_RUN:
                for lab in current_projects:
                    issue.remove_from_labels(lab)
                issue.add_to_labels(target_project)


        # issue is up to date!
        files_handled.add(file_name)
        continue

    # unknown issue, mark as unhandled/ignore
    print(f"Unknown issue: {issue.title}")
    if not DRY_RUN:
        issue.add_to_labels(label_unmanaged)

print("Checking for missing issues...")
for file_name, file in file_list.items():
    if file_name in files_handled:
        continue
    if file.is_implemented():
        continue
    print(f"Creating issue: Implement {file_name}")
    if not DRY_RUN:
        issue = repo.create_issue(
            title=f"Implement {file_name}",
            body=truncate(file.issue_body(), 65500, ""),
            labels=[label_implement]
        )

print("Checking status of project...")

def run_query(query): # A simple function to use requests.post to make the API call. Note the json= section.
    request = requests.post('https://api.github.com/graphql', json={'query': query}, headers={"Authorization": "Token " + PROJECT_TOKEN})
    if request.status_code == 200:
        response = request.json()
        if 'errors' in response:
            raise Exception("Query failed to run by returning error {}\nRequest: {}".format(response['errors'], query))
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))

def get_project_items(project_id):
    query = """
        {
            node(id: "PROJECT_ID") {
                ... on ProjectV2 {
                    items(first: 100, after: "AFTER") {
                        nodes {
                            id
                            title: fieldValueByName(name: "Title") {
                                ... on ProjectV2ItemFieldTextValue {
                                    text
                                }
                            }
                            status: fieldValueByName(name: "Status") {
                                ... on ProjectV2ItemFieldSingleSelectValue {
                                    field {
                                        ... on ProjectV2SingleSelectField {
                                            id
                                        }
                                    }
                                    name
                                }
                            }
                            content {
                                ...on Issue {
                                    number
                                    assignees {
                                        totalCount
                                    }
                                    repository {
                                        name
                                        owner {
                                            login
                                        }
                                    }
                                }
                            }
                        }
                        pageInfo {
                            endCursor
                            hasNextPage
                        }
                    }
                }
            }
        }
    """.replace("PROJECT_ID", project_id)
    result = run_query(query.replace(", after: \"AFTER\"", ""))
    items = result['data']['node']['items']['nodes']
    while result['data']['node']['items']['pageInfo']['hasNextPage']:
        endCursor = result['data']['node']['items']['pageInfo']['endCursor']
        result = run_query(query.replace("AFTER", endCursor))
        items += result['data']['node']['items']['nodes']
    return items

def get_issue_id(issue_number):
    return run_query("""
        {
            repository(owner: "OWNER", name: "REPO") {
                issue(number: ISSUE_ID) {
                    id
                }
            }
        }
    """.replace("OWNER", OWNER).replace("REPO", REPO).replace("ISSUE_ID", str(issue_number)))['data']['repository']['issue']['id']

def add_project_item(project_id, content_id):
    return run_query("""
        mutation {
            addProjectV2ItemById(input: {projectId: "PROJECT_ID", contentId: "CONTENT_ID"}) {
                item {
                    id
                }
            }
        }
    """.replace("PROJECT_ID", project_id).replace("CONTENT_ID", content_id))['data']['addProjectV2ItemById']['item']['id']

def delete_project_item(project_id, item_id):
    run_query("""
        mutation {
            deleteProjectV2Item(input: {projectId: "PROJECT_ID", itemId: "ITEM_ID"}) {
                deletedItemId
            }
        }
    """.replace("PROJECT_ID", project_id).replace("ITEM_ID", item_id))

def set_project_item_status(project_id, item_id, status_id, status_value_id):
    run_query("""
        mutation {
            updateProjectV2ItemFieldValue(input: {
                projectId: "PROJECT_ID",
                itemId: "ITEM_ID",
                fieldId: "STATUS_ID",
                value: {singleSelectOptionId: "DONE_ID"}
            }) {
                projectV2Item {
                    id
                }
            }
        }
    """.replace("PROJECT_ID", project_id).replace("ITEM_ID", item_id).replace("STATUS_ID", status_id).replace("DONE_ID", status_value_id))

# get project items

project_items = get_project_items(PROJECT_ID)

issues_handled = set()
for item in project_items:
    status = item['status']['name'] if item['status'] is not None else "None"
    if status == "Done":
        continue  # ignore done items
    if item['content']['repository']['name'] != REPO or item['content']['repository']['owner']['login'] != OWNER:
        continue  # ignore items from other repos

    title = item['title']['text']
    if title.startswith("Implement "):
        file_name = title.split("Implement ")[1]
        if file_name not in file_list:
            print(f"Deleting item: {title}")
            if not DRY_RUN:
                delete_project_item(PROJECT_ID, item['id'])
            continue
        file = file_list[file_name]
        if file.is_implemented():
            issues_handled.add(item['content']['number'])
            print(f"Moving item to Done: {title}")
            if not DRY_RUN:
                set_project_item_status(PROJECT_ID, item['id'], STATUS_ID, STATUS_DONE_ID)
            continue

        assignees = item['content']['assignees']['totalCount'] if item['content'] is not None else 0
        if assignees > 0 and status != "In Progress":
            print(f"Moving item to In Progress: {title}")
            if not DRY_RUN:
                set_project_item_status(PROJECT_ID, item['id'], STATUS_ID, STATUS_INPROGRESS_ID)
        elif assignees == 0 and status != "Todo":
            print(f"Moving item to Todo: {title}")
            if not DRY_RUN:
                set_project_item_status(PROJECT_ID, item['id'], STATUS_ID, STATUS_TODO_ID)

        # item is up to date!
        issues_handled.add(item['content']['number'])
        continue

    # unknown item
    print(f"Unknown item: {item.title}")

for issue in repo.get_issues(state="open"):
    if label_unmanaged in issue.labels:
        continue
    if issue.number in issues_handled:
        continue
    if issue.title.startswith("Implement "):
        print(f"Creating item: {issue.title}")
        if not DRY_RUN:
            item_id = add_project_item(PROJECT_ID, get_issue_id(issue.number))
            set_project_item_status(PROJECT_ID, item_id, STATUS_ID, STATUS_TODO_ID)
        continue
    
    print(f"Unknown issue: {issue.title}")
