# Copyright © 2020, Joseph Berry, Rico Tabor (opendrop.dev@gmail.com)
# OpenDrop is released under the GNU GPL License. You are free to
# modify and distribute the code, but always under the same license
# (i.e. you cannot make commercial derivatives).
#
# If you use this software in your research, please cite the following
# journal articles:
#
# J. D. Berry, M. J. Neeson, R. R. Dagastine, D. Y. C. Chan and
# R. F. Tabor, Measurement of surface and interfacial tension using
# pendant drop tensiometry. Journal of Colloid and Interface Science 454
# (2015) 226–237. https://doi.org/10.1016/j.jcis.2015.05.012
#
# E. Huang, T. Denning, A. Skoufis, J. Qi, R. R. Dagastine, R. F. Tabor
# and J. D. Berry, OpenDrop: Open-source software for pendant drop
# tensiometry & contact angle measurements, submitted to the Journal of
# Open Source Software
#
# These citations help us not only to understand who is using and
# developing OpenDrop, and for what purpose, but also to justify
# continued development of this code and other open source resources.
#
# OpenDrop is distributed WITHOUT ANY WARRANTY; without even the
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.  You
# should have received a copy of the GNU General Public License along
# with this software.  If not, see <https://www.gnu.org/licenses/>.


from typing import Optional, Tuple, Any

import numpy as np
import cairo

from opendrop.app.common.image_processing.image_processor import ImageProcessorPluginViewContext
from opendrop.app.common.image_processing.plugins.preview import AcquirerController, ImageSequenceAcquirerController, \
    image_sequence_navigator_cs
from opendrop.mvp import ComponentSymbol, View, Presenter
from opendrop.geometry import Rect2
from opendrop.widgets.canvas import ImageArtist, PolylineArtist
from .model import IFTPreviewPluginModel

ift_preview_plugin_cs = ComponentSymbol()  # type: ComponentSymbol[None]


@ift_preview_plugin_cs.view(options=['view_context', 'z_index'])
class IFTPreviewPluginView(View['IFTPreviewPluginPresenter', None]):
    def _do_init(self, view_context: ImageProcessorPluginViewContext, z_index: int) -> None:
        self._view_context = view_context
        self._canvas = self._view_context.canvas

        self._image_sequence_navigator_cid = None  # type: Optional[Any]

        self._bg_artist = ImageArtist()
        self._canvas.add_artist(self._bg_artist, z_index=z_index)

        self._features_artist = ImageArtist()
        self._canvas.add_artist(self._features_artist, z_index=z_index)

        self._drop_edge_artist = PolylineArtist(
            stroke_color=(0.0, 0.5, 1.0),
            stroke_width=2,
        )
        self._canvas.add_artist(self._drop_edge_artist, z_index=z_index)

        self._needle_left_edge = PolylineArtist(
            stroke_color=(0.0, 0.5, 1.0),
            stroke_width=2,
        )
        self._canvas.add_artist(self._needle_left_edge, z_index=z_index)

        self._needle_right_edge = PolylineArtist(
            stroke_color=(0.0, 0.5, 1.0),
            stroke_width=2,
        )
        self._canvas.add_artist(self._needle_right_edge, z_index=z_index)

        self.presenter.view_ready()

    def set_background_image(self, image: Optional[np.ndarray]) -> None:
        if image is None:
            self._bg_artist.clear_data()
            return

        width = image.shape[1]
        height = image.shape[0]
        self._bg_artist.extents = Rect2(0, 0, width, height)
        self._bg_artist.set_rgbarray(image)
        self._canvas.set_content_size(width, height)

        # Set zoom to minimum, i.e. scale image so it always fits.
        self._canvas.zoom(0)

    def set_edge_detection(self, mask: Optional[np.ndarray]) -> None:
        if mask is None:
            self._features_artist.clear_data()
            return

        data = np.full_like(mask, 0xff8080ff, dtype=np.uint32)
        data *= mask//255

        width = mask.shape[1]
        height = mask.shape[0]
        self._features_artist.extents = Rect2(0, 0, width, height)
        self._features_artist.set_data(data, cairo.Format.ARGB32, width, height)

    def set_drop_profile(self, drop_profile: Optional[np.ndarray]) -> None:
        if drop_profile is None:
            self._drop_edge_artist.props.polyline = None
            return

        self._drop_edge_artist.props.polyline = drop_profile

    def set_needle_profile(self, needle_profile: Optional[Tuple[np.ndarray, np.ndarray]]) -> None:
        if needle_profile is None:
            self._needle_left_edge.props.polyline = None
            self._needle_right_edge.props.polyline = None
            return

        self._needle_left_edge.props.polyline = needle_profile[0]
        self._needle_right_edge.props.polyline = needle_profile[1]

    def show_image_sequence_navigator(self) -> None:
        if self._image_sequence_navigator_cid is not None:
            return

        self._image_sequence_navigator_cid, nav_area = \
            self.new_component(
                image_sequence_navigator_cs.factory(
                    model=self.presenter.acquirer_controller
                )
            )

        nav_area.show()
        self._view_context.extras_area.add(nav_area)

    def hide_image_sequence_navigator(self) -> None:
        if self._image_sequence_navigator_cid is None:
            return

        self.remove_component(
            self._image_sequence_navigator_cid
        )

        self._image_sequence_navigator_cid = None

    def _do_destroy(self) -> None:
        self._canvas.remove_artist(self._bg_artist)
        self._canvas.remove_artist(self._features_artist)
        self._canvas.remove_artist(self._drop_edge_artist)
        self._canvas.remove_artist(self._needle_left_edge)
        self._canvas.remove_artist(self._needle_right_edge)


@ift_preview_plugin_cs.presenter(options=['model'])
class IFTPreviewPluginPresenter(Presenter['IFTPreviewPluginView']):
    def _do_init(self, model: IFTPreviewPluginModel) -> None:
        self._model = model
        self.__event_connections = []

    def view_ready(self) -> None:
        self._model.watch()

        self.__event_connections.extend([
            self._model.bn_source_image.on_changed.connect(
                self._update_preview_source_image,
            ),
            self._model.bn_edge_detection.on_changed.connect(
                self._update_edge_detection,
            ),
            self._model.bn_drop_profile.on_changed.connect(
                self._update_drop_profile,
            ),
            self._model.bn_needle_profile.on_changed.connect(
                self._update_needle_profile,
            ),
            self._model.bn_acquirer_controller.on_changed.connect(
                self._hdl_model_acquirer_controller_changed,
            )
        ])

        self._update_preview_source_image()
        self._update_edge_detection()
        self._update_drop_profile()
        self._update_needle_profile()
        self._hdl_model_acquirer_controller_changed()

    def _update_preview_source_image(self) -> None:
        source_image = self._model.bn_source_image.get()
        self.view.set_background_image(source_image)

    def _update_edge_detection(self) -> None:
        edge_detection = self._model.bn_edge_detection.get()
        self.view.set_edge_detection(edge_detection)

    def _update_drop_profile(self) -> None:
        drop_profile = self._model.bn_drop_profile.get()
        self.view.set_drop_profile(drop_profile)

    def _update_needle_profile(self) -> None:
        needle_profile = self._model.bn_needle_profile.get()
        self.view.set_needle_profile(needle_profile)

    def _hdl_model_acquirer_controller_changed(self) -> None:
        acquirer_controller = self.acquirer_controller

        if isinstance(acquirer_controller, ImageSequenceAcquirerController):
            self.view.show_image_sequence_navigator()
        else:
            self.view.hide_image_sequence_navigator()

    @property
    def acquirer_controller(self) -> Optional[AcquirerController]:
        return self._model.bn_acquirer_controller.get()

    def _do_destroy(self):
        for ec in self.__event_connections:
            ec.disconnect()

        self._model.unwatch()
