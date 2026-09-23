
from typing import Dict, Optional

import requests
from atlassian import ConfluenceV2

class MyConfluence:
    def __init__(self, api_token, email, base_url):
        base_url = base_url.rstrip('/')
        if base_url.endswith('/wiki'):
            base_url = base_url[:-5]

        self.confluence = ConfluenceV2(
            url=base_url,
            username=email,
            password=api_token,
            cloud=True
        )
        self._page_hierarchy: Dict[str, str] = {}

    @property
    def page_hierarchy(self) -> Dict[str, str]:
        return self.confluence.get_page_hierarchy()

    def get_page_by_title(self, space, title) -> Optional[Dict]:
        response = self.confluence.get_page_by_title(space, title, expand='ancestors')
        results = response.get("results", [])
        return results[0] if results else None

    def create_page(self, space, title, body, parent_id=None, representation=None):
        space_data = self.confluence.get_space_by_key(space)
        space_id = space_data['id'] if isinstance(space_data, dict) else space_data

        try:
            return self.confluence.create_page(
                space_id=space_id,
                title=title,
                body=body,
                parent_id=parent_id,
                representation=representation,
            )
        except requests.exceptions.HTTPError as error:
            response = error.response
            status_code = response.status_code if response is not None else 'unknown'
            response_text = response.text.strip() if response is not None else str(error)
            raise RuntimeError(
                f'Confluence page creation failed ({status_code}): {response_text}'
            ) from error

    def update_page(self, page_id, title, body):
        return self.confluence.update_page(page_id, title=title, body=body)