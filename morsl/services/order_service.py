from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from morsl.services.sse_publisher import SSEPublisher
from morsl.tandoor_api import TandoorAPI, TandoorError
from morsl.utils import now

_MAX_SERVER_ORDERS = 1000


class OrderService(SSEPublisher):
    """Order tracking via Tandoor meal plans with SSE notification.

    Orders are stored as Tandoor meal plan entries using a configured meal type.
    This provides single-source-of-truth in Tandoor with built-in history,
    analytics, and calendar integration.
    """

    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.token = token
        self.logger = logging.getLogger(__name__)
        self._api: Optional[TandoorAPI] = None
        self._cached_meal_type: Optional[Dict[str, Any]] = None
        self._cached_meal_type_id: Optional[int] = None
        self._lock = threading.Lock()
        self._init_sse()
        self._server_orders: List[Dict[str, Any]] = []

    def _get_api(self) -> TandoorAPI:
        """Lazy-initialize API client (thread-safe)."""
        with self._lock:
            if self._api is None:
                if not hasattr(self.logger, "loglevel"):
                    self.logger.loglevel = self.logger.level
                self._api = TandoorAPI(self.url, self.token, self.logger)
            return self._api

    def _get_meal_type(self, meal_type_id: Optional[int] = None) -> Dict[str, Any]:
        """Get the meal type for orders (thread-safe).

        If meal_type_id is provided, fetch that specific type from Tandoor.
        Otherwise use the first available meal type.
        Raises RuntimeError if no meal types exist.
        """
        if meal_type_id is not None:
            with self._lock:
                if self._cached_meal_type and self._cached_meal_type_id == meal_type_id:
                    return self._cached_meal_type
            # Network I/O outside lock
            api = self._get_api()
            try:
                mt = api.get_meal_type(meal_type_id)
            except TandoorError:
                self.logger.warning(
                    f"Configured meal type {meal_type_id} not found, "
                    "falling back to first available"
                )
            else:
                with self._lock:
                    self._cached_meal_type = mt
                    self._cached_meal_type_id = meal_type_id
                self.logger.info(f"Using configured meal type: {mt['id']} - {mt['name']}")
                return mt

        # Use first available meal type
        with self._lock:
            if self._cached_meal_type is not None and (
                meal_type_id is not None or self._cached_meal_type_id is None
            ):
                return self._cached_meal_type
        # Network I/O outside lock
        api = self._get_api()
        meal_types = api.get_meal_types()
        if not meal_types:
            raise RuntimeError("No meal types configured in Tandoor")
        mt = meal_types[0]
        with self._lock:
            self._cached_meal_type = mt
            self._cached_meal_type_id = None
        self.logger.info(f"Using first available meal type: {mt['id']} - {mt['name']}")
        return self._cached_meal_type

    def place_order(
        self,
        recipe_id: int,
        recipe_name: str,
        servings: int = 1,
        customer_name: Optional[str] = None,
        meal_type_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Record an order as a Tandoor meal plan entry and notify SSE subscribers."""
        api = self._get_api()
        meal_type = self._get_meal_type(meal_type_id)

        # Create meal plan entry in Tandoor
        timestamp = now()
        name_part = f"by {customer_name} " if customer_name else ""
        meal_plan = api.create_order_meal_plan(
            recipe_id=recipe_id,
            recipe_name=recipe_name,
            meal_type=meal_type,
            servings=servings,
            note=f"Ordered {name_part}at {timestamp.strftime('%H:%M:%S')}",
            date=timestamp,
        )

        # Build order response
        order = {
            "id": str(meal_plan["id"]),
            "recipe_id": recipe_id,
            "recipe_name": recipe_name,
            "timestamp": timestamp.isoformat(),
            "servings": servings,
            "meal_plan_id": meal_plan["id"],
            "customer_name": customer_name,
        }

        self._notify_subscribers(order)
        return order

    def store_and_notify(self, order: Dict[str, Any]) -> None:
        """Store an order in the server-side in-memory list and notify SSE subscribers."""
        with self._lock:
            self._server_orders.append(order)
            if len(self._server_orders) > _MAX_SERVER_ORDERS:
                self._server_orders = self._server_orders[-_MAX_SERVER_ORDERS:]
        self._notify_subscribers(order)

    def store_order(self, order: Dict[str, Any]) -> None:
        """Store an order in the server-side in-memory list."""
        with self._lock:
            self._server_orders.append(order)
            if len(self._server_orders) > _MAX_SERVER_ORDERS:
                self._server_orders = self._server_orders[-_MAX_SERVER_ORDERS:]

    def get_server_orders(
        self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Return server-stored orders filtered by date range, newest first."""
        if from_date is None:
            from_date = now()
        if to_date is None:
            to_date = from_date

        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")

        with self._lock:
            snapshot = list(self._server_orders)

        filtered = []
        for o in snapshot:
            order_date = o.get("timestamp", "")[:10]
            if from_str <= order_date <= to_str:
                filtered.append(o)

        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return filtered

    def delete_server_order(self, order_id: str) -> None:
        """Remove a server-stored order by ID. Raises RuntimeError if not found."""
        with self._lock:
            for i, o in enumerate(self._server_orders):
                if o.get("id") == order_id:
                    self._server_orders.pop(i)
                    return
        raise RuntimeError(f"Server order not found: {order_id}")

    def clear_server_orders(
        self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
    ) -> int:
        """Remove server-stored orders matching date range. Returns count deleted."""
        if from_date is None:
            from_date = now()
        if to_date is None:
            to_date = from_date

        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")

        with self._lock:
            before_count = len(self._server_orders)
            self._server_orders = [
                o
                for o in self._server_orders
                if not (from_str <= o.get("timestamp", "")[:10] <= to_str)
            ]
            return before_count - len(self._server_orders)

    def get_orders(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        meal_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return all orders for date range, newest first.

        Merges Tandoor meal plan orders with server-stored orders.
        Defaults to today if no dates provided.
        """
        if from_date is None:
            from_date = now()
        if to_date is None:
            to_date = from_date

        # Get server-stored orders
        server_orders = self.get_server_orders(from_date, to_date)

        # Get Tandoor orders
        tandoor_orders = self._get_tandoor_orders(from_date, to_date, meal_type_id)

        # Merge and sort by timestamp descending
        all_orders = tandoor_orders + server_orders
        all_orders.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_orders

    def _get_tandoor_orders(
        self, from_date: datetime, to_date: datetime, meal_type_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch orders from Tandoor meal plans."""
        api = self._get_api()
        meal_type = self._get_meal_type(meal_type_id)

        meal_plans = api.get_meal_plans_by_type(
            meal_type_id=meal_type["id"],
            from_date=from_date,
            to_date=to_date,
        )

        orders = []
        for mp in meal_plans:
            recipe = mp.get("recipe") or {}
            note = mp.get("note", "")
            customer_name = self._parse_customer_name(note)
            timestamp = self._build_timestamp(mp.get("from_date", ""), note)
            orders.append(
                {
                    "id": str(mp["id"]),
                    "recipe_id": recipe.get("id"),
                    "recipe_name": mp.get("title") or recipe.get("name", "Unknown"),
                    "timestamp": timestamp,
                    "servings": mp.get("servings", 1),
                    "meal_plan_id": mp["id"],
                    "note": note,
                    "customer_name": customer_name,
                }
            )

        return orders

    def get_order_counts(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        meal_type_id: Optional[int] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """Per-recipe order counts for date range."""
        orders = self.get_orders(from_date, to_date, meal_type_id=meal_type_id)
        counts: Dict[int, Dict[str, Any]] = {}

        for o in orders:
            rid = o["recipe_id"]
            if rid is None:
                continue
            if rid not in counts:
                counts[rid] = {"recipe_id": rid, "recipe_name": o["recipe_name"], "count": 0}
            counts[rid]["count"] += o.get("servings", 1)

        return counts

    def delete_order(self, order_id: str) -> None:
        """Delete a single order. Routes to server store or Tandoor based on ID prefix."""
        if order_id.startswith("local-"):
            self.delete_server_order(order_id)
        else:
            api = self._get_api()
            api.delete_meal_plan(int(order_id))

    def clear_orders(
        self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
    ) -> int:
        """Clear all orders for date range. Returns count of deleted orders."""
        # Clear server-stored orders
        server_count = self.clear_server_orders(from_date, to_date)

        # Clear Tandoor orders
        tandoor_orders = self._get_tandoor_orders(
            from_date or now(),
            to_date or from_date or now(),
        )
        api = self._get_api()
        for order in tandoor_orders:
            api.delete_meal_plan(order["meal_plan_id"])

        return len(tandoor_orders) + server_count

    @staticmethod
    def _build_timestamp(from_date: str, note: str) -> str:
        """Combine Tandoor's from_date (date only) with the time from the order note.

        Tandoor meal plans store from_date as midnight. The actual order time
        is in the note: 'Ordered [by name] at HH:MM:SS'.
        """
        # Extract time from note (always at the end after " at ")
        at_pos = note.rfind(" at ")
        time_str = note[at_pos + 4 :].strip() if at_pos >= 0 else ""
        if not time_str:
            return from_date
        # Extract just the date part from from_date (may be ISO with timezone)
        date_part = from_date[:10] if len(from_date) >= 10 else from_date
        try:
            datetime.strptime(time_str, "%H:%M:%S")
            return f"{date_part}T{time_str}"
        except ValueError:
            return from_date

    @staticmethod
    def _parse_customer_name(note: str) -> Optional[str]:
        """Extract customer name from order note.

        Notes follow the format 'Ordered by {name} at HH:MM:SS' or 'Ordered at HH:MM:SS'.
        Uses rfind to handle names that contain the word 'at'.
        """
        if not note.startswith("Ordered by "):
            return None
        at_pos = note.rfind(" at ")
        if at_pos <= len("Ordered by "):
            return None
        return note[len("Ordered by ") : at_pos]
