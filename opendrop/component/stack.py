from typing import Generic, TypeVar, MutableMapping, Optional, Sequence

from gi.repository import Gtk

from opendrop.component.gtk_widget_view import GtkWidgetView
from opendrop.utility.events import Event
from opendrop.utility.bindable import AccessorBindable

KeyType = TypeVar('KeyType')
ChildType = TypeVar('ChildType')


class StackModel(Generic[KeyType, ChildType]):
    def __init__(self) -> None:
        self._visible_child_key = None  # type: Optional[KeyType]
        self.bn_visible_child_key = AccessorBindable(
            self._get_visible_child_key,
            self._set_visible_child_key)

        self.on_child_added = Event()
        self.on_child_removed = Event()

        self._key_to_child = {}  # type: MutableMapping[KeyType, ChildType]

    @property
    def visible_child_key(self) -> Optional[KeyType]:
        return self.bn_visible_child_key.get()

    @visible_child_key.setter
    def visible_child_key(self, new_key: Optional[KeyType]) -> None:
        return self.bn_visible_child_key.set(new_key)

    def add_child(self, key: KeyType, child: ChildType) -> None:
        if key is None:
            raise ValueError('Identifying key for child `{}` cannot be None'.format(child))
        elif key in self._key_to_child:
            raise ValueError('Child `{}` is already identified by key `{}`'.format(child, key))
        elif child in self._key_to_child.values():
            for k, v in self._key_to_child.items():
                if v is child:
                    old_key = k
            raise ValueError('Child `{}` already belongs to this stack, identified by key `{}`'.format(child, old_key))

        self._key_to_child[key] = child

        self.on_child_added.fire(key, child)

    def remove_child(self, child: ChildType) -> None:
        for k, v in self._key_to_child.items():
            if v is child:
                if self.visible_child_key == k:
                    self.visible_child_key = None
                del self._key_to_child[k]
                break
        else:
            raise ValueError('Child `{}` does not belong to this stack'.format(child))

        self.on_child_removed.fire(k, child)

    def clear(self) -> None:
        """Clear all children, will fire an on_child_removed event for each child removed."""
        for child in list(self._key_to_child.values()):
            self.remove_child(child)

    def get_child_from_key(self, key: Optional[KeyType]) -> Optional[ChildType]:
        """Return the child identified by `key`. If `key` is None, return None. If no child identified by `key`, raise
        ValueError."""
        if key is None:
            return None

        try:
            return self._key_to_child[key]
        except KeyError:
            raise self._create_exc_unknown_key(key)

    @property
    def children(self) -> Sequence[ChildType]:
        return list(self._key_to_child.values())

    def _get_visible_child_key(self) -> Optional[KeyType]:
        return self._visible_child_key

    def _set_visible_child_key(self, new_key: Optional[KeyType]) -> None:
        if new_key is not None and new_key not in self._key_to_child:
            raise self._create_exc_unknown_key(new_key)

        self._visible_child_key = new_key

    @staticmethod
    def _create_exc_unknown_key(key: KeyType) -> Exception:
        return ValueError('No child identified by the key `{}`'.format(key))


class StackView(GtkWidgetView[Gtk.Stack]):
    def __init__(self) -> None:
        self.widget = Gtk.Stack()
        self.widget.show()

    def add_child(self, view: GtkWidgetView) -> None:
        self.widget.add(view.widget)

    def remove_child(self, view: GtkWidgetView) -> None:
        self.widget.remove(view.widget)

    def clear(self) -> None:
        self.widget.foreach(lambda w: self.widget.remove(w))

    def set_visible_child(self, view: Optional[GtkWidgetView]) -> None:
        # Ignore if `view` is None.
        if view is None:
            return

        self.widget.set_visible_child(view.widget)


class StackPresenter(Generic[KeyType, ChildType]):
    def __init__(self, stack_model: StackModel[KeyType, ChildType], stack_view: StackView) -> None:
        # Clear the view of any existing children first.
        stack_view.clear()

        # Add existing children from the model to the view.
        for child in stack_model.children:
            stack_view.add_child(child)

        self.stack_model = stack_model
        self.stack_view = stack_view

        self.__event_connections = [
            self.stack_model.on_child_added.connect(self._hdl_stack_model_child_added),
            self.stack_model.on_child_removed.connect(self._hdl_stack_model_child_removed),
            self.stack_model.bn_visible_child_key.on_changed.connect(self._update_view_visible_child)]

        self._update_view_visible_child()

    def _hdl_stack_model_child_added(self, key: KeyType, child: ChildType) -> None:
        self.stack_view.add_child(child)

    def _hdl_stack_model_child_removed(self, key: KeyType, child: ChildType) -> None:
        self.stack_view.remove_child(child)

    def _update_view_visible_child(self) -> None:
        self.stack_view.set_visible_child(
            self.stack_model.get_child_from_key(
                self.stack_model.visible_child_key))

    def destroy(self) -> None:
        self.stack_view.clear()

        for ec in self.__event_connections:
            ec.disconnect()
