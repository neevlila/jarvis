"""
UI Automation Service for J.A.R.V.I.S. Desktop Engine.
Crawls the active Windows UI tree using uiautomation to discover interactable controls.
"""

from typing import List, Dict, Any, Optional
from desktop_engine.coordinates import BoundingBox, CoordinateSpace
from desktop_engine.models import PerceptionTarget


class UIAutomationService:
    """
    Handles Windows UI Automation interactions, walking active window nodes
    and locating native controls.
    """

    @staticmethod
    def get_ui_controls(ui_available: bool = True) -> List[PerceptionTarget]:
        """
        Crawls the foreground window's UI Automation tree to locate interactable components.
        Returns a list of PerceptionTarget objects tagged with screen/ui_automation coordinate spaces.
        """
        targets: List[PerceptionTarget] = []
        if not ui_available:
            return targets

        try:
            import uiautomation as auto

            target_hwnd = auto.GetForegroundWindow()
            if not target_hwnd:
                return targets

            fw_control = auto.ControlFromHandle(target_hwnd)
            if not fw_control:
                return targets

            interactable_types = {
                "ButtonControl", "HyperlinkControl", "MenuItemControl",
                "ListItemControl", "TabItemControl", "EditControl",
                "CheckBoxControl", "RadioButtonControl", "ComboBoxControl", "TreeItemControl"
            }

            # Safe BFS traversal to isolate COM exceptions per node
            queue = [(fw_control, 0)]
            visited = 0
            max_nodes = 150

            while queue and visited < max_nodes:
                current_ctrl, depth = queue.pop(0)
                visited += 1

                try:
                    control_type = getattr(current_ctrl, "ControlTypeName", "")
                    is_enabled = getattr(current_ctrl, "CurrentIsEnabled", False)

                    if is_enabled and control_type in interactable_types:
                        name = (getattr(current_ctrl, "Name", "") or "").strip()
                        rect = getattr(current_ctrl, "BoundingRectangle", None)
                        if name and rect and rect.width > 0 and rect.height > 0:
                            bbox = BoundingBox(
                                left=rect.left,
                                top=rect.top,
                                width=rect.width,
                                height=rect.height,
                                space=CoordinateSpace.SCREEN
                            )
                            targets.append(
                                PerceptionTarget(
                                    source="ui_automation",
                                    type=control_type,
                                    label=name,
                                    bounds=bbox,
                                    confidence=0.98,
                                    is_enabled=is_enabled,
                                    is_focused=getattr(current_ctrl, "HasKeyboardFocus", False),
                                    metadata={"depth": depth, "automation_id": getattr(current_ctrl, "AutomationId", "")}
                                )
                            )
                except Exception:
                    pass

                if depth < 6:
                    try:
                        children = current_ctrl.GetChildren()
                        if children:
                            for child in children:
                                queue.append((child, depth + 1))
                    except Exception:
                        pass
        except Exception as e:
            print(f"[UIAutomationService Warning] Failed to inspect UI tree: {e}")

        return targets

    @staticmethod
    def find_control_by_name(name: str, ui_available: bool, ui_root: Any) -> Optional[Any]:
        """
        Walks the tree to find an interactable control matching the query name.
        """
        if not ui_available or ui_root is None or not name:
            return None

        clean_name = name.strip()
        try:
            # Check button/link/menu controls
            control_types = [
                ui_root.ButtonControl,
                ui_root.HyperlinkControl,
                ui_root.MenuItemControl,
                ui_root.TextControl,
                ui_root.ListItemControl,
                ui_root.TabItemControl,
                ui_root.CheckBoxControl,
                ui_root.RadioButtonControl
            ]
            for ctor in control_types:
                try:
                    c = ctor(searchDepth=8, Name=clean_name)
                    if c.Exists(maxSearchSeconds=1):
                        return c
                except Exception:
                    continue

            # Fallback to Edit control
            try:
                edit = ui_root.EditControl(searchDepth=8, Name=clean_name)
                if edit.Exists(maxSearchSeconds=1):
                    return edit
            except Exception:
                pass
        except Exception as e:
            print(f"[UIAutomationService Warning] Find control failed: {e}")

        return None
