import merz
from math import hypot, sqrt
from mojo.UI import CurrentGlyphWindow
from mojo.subscriber import Subscriber, registerGlyphEditorSubscriber


EXT_KEY = "com.ryanbugden.architect"
EXT_LIB_KEY = EXT_KEY + ".settings"


def get_distance(x1, y1, x2, y2):
    distance = hypot(y2 - y1, x2 - x1)
    return distance

def get_line_from_coords(ref_pt, mid_pt, inner_radius, outer_radius):
    '''
    Calculate an orthogonal line that points to the mid-point, 
    but is cropped by the inner and outer radius, given a coordinate 
    along that line, and the mid-point of the circles.
    Returns start and end points as (x1, y1), (x2, y2).
    '''
    rx, ry = ref_pt
    cx, cy = mid_pt

    dx = rx - cx
    dy = ry - cy
    r = get_distance(rx, ry, cx, cy)

    # unit radial direction from center -> ref_pt
    ux, uy = dx / r, dy / r

    # endpoints on inner and outer circles along that same ray
    p1 = (cx + ux * inner_radius, cy + uy * inner_radius)
    p2 = (cx + ux * outer_radius, cy + uy * outer_radius)

    return p1, p2


class ArchitectSubscriber(Subscriber):
    
    def build(self):
        self.settings = {}
        self.glyph_editor = self.getGlyphEditor()
        self.g = self.glyph_editor.getGlyph()
        if self.g is None and hasattr(self.glyph_editor, "fontOverview"):
            self.f = self.glyph_editor.fontOverview.getFont().asFontParts()
        else:
            self.f = self.g.font.asFontParts()

    def started(self):
        if self.f is None:
            print("No current font")
            return
            
        try:
            self.g = CurrentGlyph()
        except:
            self.g = None
            print("No current glyph")
        
        self.circle_container = self.getGlyphEditor().extensionContainer(
            identifier=EXT_KEY + ".circleContainer", 
            location="background", 
            clear=True
        )
        self.cutoff_container = self.getGlyphEditor().extensionContainer(
            identifier=EXT_KEY + ".cutoffContainer", 
            location="background", 
            clear=True
        )
        self.horizontal_container = self.getGlyphEditor().extensionContainer(
            identifier=EXT_KEY + ".horizontalContainer", 
            location="background", 
            clear=True
        )
        self.vertical_container = self.getGlyphEditor().extensionContainer(
            identifier=EXT_KEY + ".verticalContainer", 
            location="foreground", 
            clear=True
        )
        self.sidebearing_container = self.getGlyphEditor().extensionContainer(
            identifier=EXT_KEY + ".sidebearingContainer",
            location="foreground", 
            clear=True
        )
        self.update_display_settings()
        self.update_drawing()

    def update_display_settings(self):
        if EXT_LIB_KEY in self.f.lib:
            self.settings = self.f.lib[EXT_LIB_KEY]
        else:
            self.settings = {}

    # glyphEditorGlyphDidChangeDelay = 0
    def glyphEditorGlyphDidChange(self, info):
        self.g = info["glyph"]
        if self.g is None:
            return
        self.update_drawing()
        # print('glyphEditorGlyphDidChange')
        
    # glyphEditorGlyphDidChangeMetricsDelay = 0.03
    def glyphEditorGlyphDidChangeMetrics(self, info):
        self.g = info["glyph"]
        if self.g is None:
            return
        self.update_drawing()
        # print('glyphEditorGlyphDidChangeMetrics')
        
    # glyphEditorDidSetGlyphDelay = 0.1
    def glyphEditorDidSetGlyph(self, info):
        self.g = info["glyph"]
        if self.g is None:
            return
        self.update_drawing() 
        # print('glyphEditorDidSetGlyph')
        
    # architectSettingsDidChangeDelay = 0
    def architectSettingsDidChange(self, info):
        self.update_display_settings()
        self.update_drawing()
        
    architectCutOffSettingDidChangeDelay = 0
    def architectCutOffSettingDidChange(self, info):
        self.update_display_settings()
        self.draw_cutoff()
        self.update_drawing()
    
    def update_drawing(self, horizontal_refresh=True):
        debug = False
        if debug:print(self.settings)
        if self.f and self.settings and self.g is not None:
            self.f = self.g.font
            

            color = tuple(self.settings["guideColor"])
            ring_ratio = self.settings["ratio"]
            flip = self.settings["flip"]
            
            if ring_ratio == 0:
                return
                
            inner_radius = (1 / ring_ratio) * self.f.info.capHeight
            outer_radius = inner_radius + self.f.info.capHeight
                
            if flip:
                mid_pt = (self.g.width / 2, self.f.info.capHeight + inner_radius)
                inner_x, inner_y = self.g.width/2 - inner_radius, self.f.info.capHeight
                outer_x, outer_y = self.g.width/2 - outer_radius, 0
            else:
                mid_pt = (self.g.width / 2, - inner_radius)
                inner_x, inner_y = self.g.width/2 - inner_radius, -inner_radius * 2
                outer_x, outer_y = self.g.width/2 - outer_radius, -outer_radius * 2 + self.f.info.capHeight
            
            # Rings
            self.circle_container.clearSublayers()
            if self.settings["showRings"]:
                self.inner_circle = self.circle_container.appendOvalSublayer(
                    position=(inner_x, inner_y),
                    size=(inner_radius * 2, inner_radius * 2),
                    fillColor=None,
                    strokeColor=color,
                    strokeWidth=1,
                )
                self.outer_circle = self.circle_container.appendOvalSublayer(
                    position=(outer_x, outer_y),
                    size=(outer_radius * 2, outer_radius * 2),
                    fillColor=None,
                    strokeColor=color,
                    strokeWidth=1,
                )
                
            # Horizontal guides
            self.horizontal_container.clearSublayers()
            if self.settings["showHorizontal"]:
                # for c in self.g:
                #     for pt in c.points:
                #         if pt.type != "offcurve":
                #             if 1/10 * self.f.info.capHeight < pt.y < self.f.info.capHeight * 9/10:
                #                 self.draw_horizontal((pt.x, pt.y), mid_pt, color)
                for y in self.settings["horizontalYs"]:
                    self.draw_horizontal((self.g.width/2, y), mid_pt, color)
            
            # Vertical lines (general)
            self.vertical_container.clearSublayers()
            # Vertical guides
            outer_padding = 12  # Hard-coded padding outside the radius from which vertical guides may be drawn if cutoff isn’t maxed.
            if self.settings["showVertical"]:
                if debug: print("Show Vertical is on.")
                cutoff = self.settings["cutOff"]
                for c in self.g:
                    for pt in c.points:
                        if pt.type != "offcurve":
                            pt_distance = get_distance(pt.x, pt.y, *mid_pt)
                            if outer_radius + outer_padding > pt_distance > inner_radius + self.f.info.capHeight * cutoff:
                                if cutoff != 1:
                                    if debug: print("Making vertical line here", (pt.x, pt.y))
                                    self.draw_line(self.vertical_container, (pt.x, pt.y), mid_pt, color)
            # Sidebearings
            self.sidebearing_container.clearSublayers()
            outer_padding = 12  # Hard-coded padding outside the radius from which vertical guides may be drawn if cutoff isn’t maxed.
            if self.settings["showSidebearings"]:
                y = self.f.info.capHeight if flip else 0
                coords = [(0, y), (self.g.width, y)]
                for coord in coords:
                    line = get_line_from_coords(coord, mid_pt, inner_radius, outer_radius)
                    self.draw_line(self.sidebearing_container, *line, color, dash=False)

    def draw_line(self, container, p1, p2, color, dash=True):
        new_line = container.appendLineSublayer(
            startPoint=p1,
            endPoint=p2,
            strokeColor=color,
            strokeWidth=1,
            strokeDash=(5, 8) if dash else None
            )
            
    def draw_horizontal(self, pt_coord, mid_pt, color):
        radius = get_distance(*pt_coord, *mid_pt)
        x, y = mid_pt[0] - radius, mid_pt[1] - radius
        new_circle = self.horizontal_container.appendOvalSublayer(
            position=(x, y),
            size=(radius * 2, radius * 2),
            fillColor=None,
            strokeColor=color,
            strokeWidth=1,
            strokeDash=(5, 8)
            )      
            
    def draw_cutoff(self):
        if "cutOff" not in self.settings:
            return
        cutoff = self.settings["cutOff"]
        r,g,b,a = self.settings["guideColor"] 
        flip = self.settings["flip"] 
        color = (r,g,b,a/3)
        ring_ratio   = self.settings["ratio"]
        inner_radius = (1 / ring_ratio) * self.f.info.capHeight
        radius = inner_radius + (cutoff  * self.f.info.capHeight)
        if flip:
            x, y = self.g.width/2 - radius, self.f.info.capHeight - (cutoff * self.f.info.capHeight)
        else:
            x, y = self.g.width/2 - radius, (cutoff * self.f.info.capHeight) - (radius * 2)
        self.cutoff_container.clearSublayers()
        cutoff_circle = self.cutoff_container.appendOvalSublayer(
            position=(x, y),
            size=(radius * 2, radius * 2),
            fillColor=color,
            # strokeColor=self.settings["guideColor"] ,
            # strokeWidth=1,
            # strokeDash=(5,5)
        )
        with cutoff_circle.propertyGroup(
                duration=1.5,
            ):
            # cutoff_circle.setFillColor(color)
            cutoff_circle.setFillColor((0, 0, 0, 0))


registerGlyphEditorSubscriber(ArchitectSubscriber)