"""Attribute filtering and name resolution."""

import json
import logging
from typing import Any

from .utils import normalize_id

logger = logging.getLogger(__name__)


class AttributeFilter:
    """Handles attribute filtering and name resolution."""

    def __init__(self, filter_data: dict[str, dict[str, Any]] | None = None):
        """Initialize the filter.

        Args:
            filter_data: Dictionary mapping cluster_id -> {name, attributes}.
        """
        self.filter_data = filter_data

    @staticmethod
    def from_file(filter_file: str | None) -> "AttributeFilter":
        """Load attribute filter from JSON file.

        Expected JSON format:
        {
            "cluster_id": {
                "name": "cluster_name",
                "attributes": {
                    "attribute_id": "attribute_name",
                    "attribute_id_2": "attribute_name_2"
                }
            }
        }

        Returns AttributeFilter with no filter (allows all) if file not provided.
        """
        if not filter_file:
            return AttributeFilter(None)

        try:
            with open(filter_file, "r") as f:
                filter_dict = json.load(f)

            if not isinstance(filter_dict, dict):
                logger.error("Filter file must contain a JSON object, got %s", type(filter_dict))
                return AttributeFilter(None)

            # Normalize all cluster and attribute IDs to strings
            normalized_filter = {}
            for cluster_id, cluster_data in filter_dict.items():
                # Normalize cluster ID from hex to decimal if needed
                cluster_str = normalize_id(cluster_id)

                if not isinstance(cluster_data, dict):
                    logger.warning("Cluster %s data must be a dict, skipping", cluster_id)
                    continue

                cluster_name = str(cluster_data.get("name", cluster_str))
                attributes = cluster_data.get("attributes", {})

                if not isinstance(attributes, dict):
                    logger.warning("Attributes for cluster %s must be a dict, skipping", cluster_id)
                    continue

                # Normalize attribute IDs to decimal strings
                normalized_attributes = {normalize_id(attr_id): str(attr_name)
                                        for attr_id, attr_name in attributes.items()}

                normalized_filter[cluster_str] = {
                    "name": cluster_name,
                    "attributes": normalized_attributes
                }

            logger.info("Loaded attribute filter from %s: %s cluster(s)", filter_file, len(normalized_filter))
            return AttributeFilter(normalized_filter)

        except FileNotFoundError:
            logger.error("Filter file not found: %s", filter_file)
            return AttributeFilter(None)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in filter file: %s", e)
            return AttributeFilter(None)

    def is_allowed(self, cluster_id: str, attribute_id: str) -> bool:
        """Check if an attribute is allowed by the filter.

        If no filter is set, all attributes are allowed.
        """
        if self.filter_data is None:
            return True

        if cluster_id not in self.filter_data:
            return False

        attributes = self.filter_data[cluster_id].get("attributes", {})
        return attribute_id in attributes

    def get_cluster_name(self, cluster_id: str) -> str | None:
        """Get the cluster name from the filter, or None if not found."""
        if self.filter_data is None or cluster_id not in self.filter_data:
            return None
        return self.filter_data[cluster_id].get("name")

    def get_attribute_name(self, cluster_id: str, attribute_id: str) -> str | None:
        """Get the attribute name from the filter, or None if not found."""
        if self.filter_data is None or cluster_id not in self.filter_data:
            return None
        attributes = self.filter_data[cluster_id].get("attributes", {})
        return attributes.get(attribute_id)
