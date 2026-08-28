class colorTheme:
    def __init__(self, 
                 name, 
                 textColorMain, 
                 textColorSecondary, 
                 backgroundGradientDark, 
                 backgroundGradientLight, 
                 buttonDisabled, 
                 buttonGradientDark, 
                 buttonGradientLight, 
                 darkAccent, 
                 lightAccent, 
                 borderColor, 
                 selectedColor, 
                 hoverColor, 
                 currentSongColor,
                 statusHighlight):
        self.name = name
        self.textColorMain = textColorMain
        self.textColorSecondary = textColorSecondary
        self.backgroundGradientDark = backgroundGradientDark
        self.backgroundGradientLight = backgroundGradientLight
        self.buttonDisabled = buttonDisabled
        self.buttonGradientDark = buttonGradientDark
        self.buttonGradientLight = buttonGradientLight
        self.darkAccent = darkAccent
        self.lightAccent = lightAccent
        self.borderColor = borderColor
        self.selectedColor = selectedColor
        self.hoverColor = hoverColor
        self.currentSongColor = currentSongColor
        self.currentSongColorLight = self._lighten_color(currentSongColor, 0.3)
        self.statusHighlight = statusHighlight

    def _lighten_color(self, hex_color, amount):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r + (255 - r) * amount))
        g = min(255, int(g + (255 - g) * amount))
        b = min(255, int(b + (255 - b) * amount))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    @staticmethod
    def getDarkGrayTheme():
        return colorTheme(
                name='Dark Gray Theme',
                textColorMain='#E0E0E0',       
                textColorSecondary="#FFFFFF",    
                backgroundGradientDark='#121212', 
                backgroundGradientLight='#1E1E1E',
                buttonDisabled="#1C1C1C",        
                buttonGradientDark='#2F2F2F',  
                buttonGradientLight='#3A3A3A',  
                darkAccent="#606060",          
                lightAccent='#6FB8FF',          
                borderColor='#2C2C2C',           
                selectedColor='#3A8DFF',       
                hoverColor='#2A2A2A',            
                currentSongColor="#49A4FF",    
                statusHighlight= "0, 0, 0", 
        )

    @staticmethod
    def getDefaultTheme():
        return colorTheme(
            name='Just Dance Theme', 
            textColorMain='#ffffff', 
            textColorSecondary="#000000", 
            backgroundGradientDark="#8B2361", 
            backgroundGradientLight='#C71585', 
            buttonDisabled='#4A0E32', 
            buttonGradientDark='#FFA07A', 
            buttonGradientLight='#FF69B4', 
            darkAccent='#4A0E32', 
            lightAccent='#FF69B4', 
            borderColor='#FF69B4', 
            selectedColor='#FF69B4', 
            hoverColor="#FC6CA1", 
            currentSongColor='#FF9FCF',
            statusHighlight="255, 255, 255",
        )
    @staticmethod
    def getDarkBlueTheme():
        return colorTheme(
            name='Ocean Blue Theme',
            textColorMain='#E6EDF3',
            textColorSecondary="#FFFFFF",
            backgroundGradientDark="#000040",
            backgroundGradientLight="#060655",
            buttonDisabled="#1A1F2E",
            buttonGradientDark="#0A0A8C",
            buttonGradientLight="#2651BC",
            darkAccent="#021335",
            lightAccent='#3A6FD8',
            borderColor="#4D6AA5",
            hoverColor="#1F3F7A",
            selectedColor='#2A5BBF',
            currentSongColor="#3A7BFF",
            statusHighlight="255, 255, 255",
        )
    @staticmethod
    def getBloodRedTheme():
        return colorTheme(
            name='Blood Red Theme',
            textColorMain='#F2F2F2',
            textColorSecondary="#FFFFFF",
            backgroundGradientDark="#1A0000",
            backgroundGradientLight="#330000",
            buttonDisabled="#2A0A0A",
            buttonGradientDark="#4A0000",
            buttonGradientLight="#8B0000",
            darkAccent="#4E0E0E",
            lightAccent="#FF3B3B",
            borderColor="#811F1F",
            selectedColor="#BF1212",
            hoverColor="#2A0000",
            currentSongColor="#FF4D4D",
            statusHighlight="0, 0, 0",
        )
    @staticmethod
    def getBlackTheme():
        return colorTheme(
            name='Black Theme',
            textColorMain='#E6E6E6',
            textColorSecondary="#FFFFFF",
            backgroundGradientDark="#000000",
            backgroundGradientLight="#0A0A0A",
            buttonDisabled="#111111",
            buttonGradientDark="#1A1A1A",
            buttonGradientLight="#2A2A2A",
            darkAccent="#0D0D0D",
            lightAccent="#666666",
            borderColor="#1F1F1F",
            selectedColor="#808080",
            hoverColor="#141414",
            currentSongColor="#AAAAAA",
            statusHighlight="0, 0, 0",
        )
    @staticmethod
    def getWhiteTheme():
        return colorTheme(
            name='White Theme',
            textColorMain='#1A1A1A',
            textColorSecondary="#FFFFFF",
            backgroundGradientDark="#E6E6E6",
            backgroundGradientLight="#F5F5F5",
            buttonDisabled="#CFCFCF",
            buttonGradientDark="#D9D9D9",
            buttonGradientLight="#FFFFFF",
            darkAccent="#A6A6A6",
            lightAccent="#4DA3FF",
            borderColor="#BDBDBD",
            selectedColor="#4D4D4D",
            hoverColor="#DDDDDD",
            currentSongColor="#4DA3FF",
            statusHighlight="0, 0, 0",
        )
    @staticmethod
    def getForestGreenTheme():
        return colorTheme(
            name='Grass Theme',
            textColorMain='#E8F5E9',
            textColorSecondary="#FFFFFF",
            backgroundGradientDark="#0B1F14",
            backgroundGradientLight="#123524",
            buttonDisabled="#1A2E22",
            buttonGradientDark="#145A32",
            buttonGradientLight="#1E8449",
            darkAccent="#164D33",
            lightAccent="#58D68D",
            borderColor="#2A8D58",
            selectedColor="#2ECC71",
            hoverColor="#48C689",
            currentSongColor="#58D68D",
            statusHighlight="255, 255, 255",
        )
    @staticmethod
    def greenAndBrownTheme():
        return colorTheme(
            name='Forest Theme',
            textColorMain='#E8F5E9',
            textColorSecondary="#000000",
            backgroundGradientDark="#1B2A1F", 
            backgroundGradientLight="#2E4A36",
            buttonDisabled="#3B2F2F",          
            buttonGradientDark="#4E342E",       
            buttonGradientLight="#6D4C41",     
            darkAccent="#2F5D3A",          
            lightAccent='#66BB6A',         
            borderColor="#3E2723",      
            selectedColor='#81C784',        
            hoverColor="#5C8A64",
            currentSongColor="#A5D6A7",
            statusHighlight="200, 230, 201",
    )

    @staticmethod
    def getGrayTheme():
        return colorTheme(
            name='Gray Theme',
            textColorMain="#000000",
            textColorSecondary="#FFFFFF",
            backgroundGradientDark="#8A8A8A",
            backgroundGradientLight="#C5C5C5",
            buttonDisabled="#B5B5B5",      
            buttonGradientDark="#9A9A9A",  
            buttonGradientLight="#CACACA",   
            darkAccent="#939393",           
            lightAccent="#5CAEFF",     
            borderColor="#C5C5C5",          
            selectedColor="#3A8DFF",      
            hoverColor="#A4A4A4",       
            currentSongColor="#5CAEFF",     
            statusHighlight="0, 0, 0",
        )
    @staticmethod
    def getAllThemesAsDict():
        return {
            "default_theme": colorTheme.getDefaultTheme(),
            "light_theme": colorTheme.getWhiteTheme(),
            "gray_theme": colorTheme.getGrayTheme(),
            "dark_gray_theme": colorTheme.getDarkGrayTheme(),
            "black_theme": colorTheme.getBlackTheme(),
            "dark_blue_theme": colorTheme.getDarkBlueTheme(),
            "blood_red_theme": colorTheme.getBloodRedTheme(),
            "forest_green_theme": colorTheme.getForestGreenTheme(),
            "green_and_brown_theme": colorTheme.greenAndBrownTheme(),
        }