import socket
import ssl
import tkinter
import tkinter.font

FONTS = {}
def get_font(size, weight, slant):
    key = (size, weight, slant)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight,
            slant=slant)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
    def request(self):
        s = socket.socket(
            family=socket.AF_INET, #ipv4
            type=socket.SOCK_STREAM, #データ量を任意
            proto=socket.IPPROTO_TCP, #TCP
        )
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        s.connect((self.host, self.port))
        s.send(("GET {} HTTP/1.0\r\n".format(self.path) + \
                "Host: {}\r\n\r\n".format(self.host)) \
               .encode("utf8"))#テキストをバイトへ変換
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        body = response.read()
        s.close()
        return body

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100

class Text: 
    def __init__(self, text):
            self.text = text

    def __repr__(self):
        return "Text('{}')".format(self.text)
class Tag:
    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return "Tag('{}')".format(self.tag)
    
class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window, 
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        # font
        bi_times = tkinter.font.Font(
            family="Times",
            size=16,
            weight="bold",
            slant="italic",
        )
    def load(self, url):
        body = url.request()
        text = lex(body)
        self.display_list = layout(text)
        self.draw()
        
    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)
    

    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()

def lex(body):
    out = []
    buffer = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if buffer: out.append(Text(buffer))
            buffer = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(buffer))
            buffer = ""
        else:
            buffer += c
    if not in_tag and buffer:
        out.append(Text(buffer))
    return out

def layout(tokens):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for tok in tokens:
        if isinstance(tok, Text):
            for word in tok.text.split():
                display_list.append((cursor_x, cursor_y, word))
                cursor_x += HSTEP * len(word)
                if cursor_x >= WIDTH - HSTEP:
                    cursor_y += VSTEP
                    cursor_x = HSTEP
    return display_list

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()


class Layout:
    def __init__(self, tokens):
        self.display_list = []
        for tok in tokens:
            self.token(tok)
        self.line = []
        self.flush()
    def token(self, tok):
        if isinstance(tok, Text):
            self.text(tok)
        elif isinstance(tok, Tag):
            self.tag(tok)
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
            self.flush()
        self.cursor_y += VSTEP

    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        if self.cursor_x + w > WIDTH - HSTEP:
            self.flush()
        font = tkinter.font.Font(
        size=16,
        weight=self.weight,
        slant=self.style,
        )
        w = font.measure(word)
        self.line.append((self.cursor_x, word, font))
    def flush(self):
        if not self.line: return
        max_ascent = max([font.metrics("ascent")
        for x, word, font in self.line])

        