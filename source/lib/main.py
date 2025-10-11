# menuTitle: Architect

import ezui
from mojo.subscriber import Subscriber, registerRoboFontSubscriber, getRegisteredSubscriberEvents, registerSubscriberEvent
from mojo.events import postEvent


EXT_KEY = "com.ryanbugden.architect"
EXT_LIB_KEY = EXT_KEY + ".settings"


def reset_defaults():
    for font in AllFonts():
        if EXT_LIB_KEY in font.lib.keys():
            del font.lib[EXT_LIB_KEY]
  
# reset_defaults()         

class ArchitectWindow(Subscriber, ezui.WindowController):
    
    debug = False

    def build(self):
        content = """

        |-fonts----|       @fontsTable
        |          |
        |----------|
        
        ---
        
        * TwoColumnForm    @form
        
        > : Show:
        > [ ] Rings        @showRings
        > [ ] Vertical     @showVertical
        > [ ] Horizontal   @showHorizontal
        
        > : Top:
        > (X) Cap-Height   
        > ( ) X-Height
        
        > : Bottom:
        > (X) Baseline
        > ( ) Descender
        
        > : V Cutoff:
        > ---X---          @cutOff
        
        > : H Guides:
        > [_ _]            @horizontalYs
        > ( Add Selected)  @addSelectedYs
        
        > : Color:
        > * ColorWell      @guideColor

        > : Ratio:
        > * HorizontalStack
        >> [_ _]           @ratio
        >> [ ] Flip        @flip
        
        > ---
        
        > : Inner Radius:
        > 100              @innerRadius

        > : Letter Height:
        > 100              @letterHeight
        """
        descriptionData = dict(
            fontsTable=dict(
                items=AllFonts(),
                allowsDropBetweenRows=False,
                allowsInternalDropReordering=False,
                width='fill',
                height=100,
                columnDescriptions=[
                    dict(
                        identifier="path",
                        title="Path",
                        cellDescription=dict(
                            cellClassArguments=dict(
                                showFullPath=False
                            )
                        )
                    ),
                ]
            ),
            form=dict(
                titleColumnWidth=90, 
                itemColumnWidth=130, 
            ),
            # innerRadius=dict(
            #     value=50,
            #     valueType="integer",
            #     valueIncrement=1,
            #     valueWidth=50,
            # ),
            # letterHeight=dict(
            #     value=50,
            #     valueType="integer",
            #     valueIncrement=1,
            #     valueWidth=50,
            # ),
            ratio=dict(
                value=0.5,
                minValue=0.01,
                valueType="float",
                valueIncrement=0.01,
                valueWidth=75,
                width=75,
            ),
            cutOff=dict(
                minValue=0,
                maxValue=1,
                value=0.5
            ),
            horizontalYs=dict(
                valueType="integerList",
            ),
            addSelectedYs=dict(
                width="fill"
            ),
        )
        self.w = ezui.EZPanel(
            content=content,
            title="Architect",
            descriptionData=descriptionData,
            controller=self
        )
        self.w.getNSWindow().setTitlebarAppearsTransparent_(True)
        self.fonts = []
        self.w.getItem("guideColor").set((1,0,0,1))
        table = self.w.getItem("fontsTable")
        if table.get():
            table.setSelectedIndexes([0])

    def started(self):
        self.w.open()
        
    def fontDocumentDidOpen(self, sender):
        self.update_fonts_table()
        
    def fontDocumentDidClose(self, sender):
        self.update_fonts_table()
        
    def fontsTableSelectionCallback(self, sender):
        table = self.w.getItem("fontsTable")
        self.fonts = table.getSelectedItems()
        self.update_form()
        
    def addSelectedYsCallback(self, sender):
        h_guides_field = self.w.getItem("horizontalYs")
        g = CurrentGlyph()
        values = h_guides_field.get()
        for pt in g.selectedPoints:
            if pt.y not in values:
                values.append(pt.y) 
        h_guides_field.set(values)
        self.formCallback(self.w.getItem("form"))
        
    def update_fonts_table(self):
        table = self.w.getItem("fontsTable")
        table.set(AllFonts())
        
    def update_form(self):
        if self.fonts:
            for item_name, value in self.w.getItem("form").getItemValues().items():
                self.w.getItem(item_name).enable(True)
                values = []
                print(item_name, value)
                for font in self.fonts:
                    if EXT_LIB_KEY in font.lib:
                        if item_name in font.lib[EXT_LIB_KEY].keys():
                            value = font.lib[EXT_LIB_KEY][item_name]
                            if value not in values:
                                values.append(font.lib[EXT_LIB_KEY][item_name])
                    # Note to self: store empty values
                if len(values) == 1:
                    self.w.getItem(item_name).set(list(values)[0])     
        else:
            for item_name, value in self.w.getItem("form").getItemValues().items():
                self.w.getItem(item_name).enable(False)
        self.update_info_labels()
        
    def update_info_labels(self):
        ratio = self.w.getItem("ratio").get()
        for item_name in ["letterHeight", "innerRadius"]:
            if ratio in (None, 0) or not self.fonts:
                self.w.getItem(item_name).set("")
                continue
            values = set()
            for font in self.fonts:
                data = {
                    "letterHeight": font.info.capHeight, 
                    "innerRadius": round(font.info.capHeight / ratio, 2)
                    }
                values.add(data[item_name])
            if len(values) == 1:
                self.w.getItem(item_name).set(list(values)[0])     
                
    def formCallback(self, sender):
        self.update_info_labels()
        for font in self.fonts:
            font.lib[EXT_LIB_KEY] = sender.get()
            if self.debug: print("This is in the font lib", font.lib[EXT_LIB_KEY])
        postEvent(f"{EXT_KEY}.architectSettingsDidChange")
        
    def cutOffCallback(self, sender):
        for font in self.fonts:
            font.lib[EXT_LIB_KEY] = self.w.getItem("form").get()
        postEvent(f"{EXT_KEY}.architectCutOffSettingDidChange")
        
    # def flipCallback(self, sender):
    #     ratio = self.w.getItem("ratio").get()
    #     if ratio:
    #         self.w.getItem("ratio").set(-ratio)
    #     self.formCallback(self.w.getItem("form"))
    
    
                
if __name__ == '__main__':
    # Register a subscriber event for when Eyeliner settings change
    event_name = f"{EXT_KEY}.architectSettingsDidChange"
    if event_name not in getRegisteredSubscriberEvents():
        registerSubscriberEvent(
            subscriberEventName=event_name,
            methodName="architectSettingsDidChange",
            lowLevelEventNames=[event_name],
            dispatcher="roboFont",
            documentation="Sent when Architect extension settings have changed.",
            delay=None
        )
    event_name = f"{EXT_KEY}.architectCutOffSettingDidChange"
    if event_name not in getRegisteredSubscriberEvents():
        registerSubscriberEvent(
            subscriberEventName=event_name,
            methodName="architectCutOffSettingDidChange",
            lowLevelEventNames=[event_name],
            dispatcher="roboFont",
            documentation="Sent when Architect cut-off setting has changed.",
            delay=None
        )
    registerRoboFontSubscriber(ArchitectWindow)