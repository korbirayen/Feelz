import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk

from Extensions import loading, tooltip, hover
import threading

from Extensions import twitter
import validators
import socket

import sqlite3
import glob
from pathlib import Path

from Extensions import vision, voice, DepressionScore, PolarityScore
from Extensions.branding import APP_NAME, LANDING_LINES, LANDING_TITLE
from Extensions.theme_store import ThemeStore
import pickle

# --- Design constants ---------------------------------------------------
# One accent color, semantic colors for results, and a fixed layout grid
# (the window is a fixed 900x650, so pixel constants are simpler and more
# precise here than relx/rely fractions).
ACCENT = '#ecb22e'
ACCENT_HOVER = '#d7a51e'
ACCENT_TEXT = '#2b2110'   # dark text on top of the accent color, readable in both themes
POSITIVE = '#1f9d55'
NEUTRAL = '#d9a441'
NEGATIVE = '#d1453b'

RAIL_W = 190      # left nav rail width
HEADER_H = 92     # top bar height (page title + segmented control)
CONTENT_X = RAIL_W + 8
CONTENT_Y = HEADER_H + 8
CONTENT_W = 900 - CONTENT_X - 12
CONTENT_H = 650 - CONTENT_Y - 10

PAD = 45                       # left/right margin inside the content area
FIELD_W = CONTENT_W - 2 * PAD  # width shared by inputs and result cards

# Nav rail rows: 4 input modes stacked at the top, Settings pinned near the bottom
NAV_ORDER = ['text', 'doc', 'voice', 'link', 'settings']
NAV_ITEM_Y = [84, 134, 184, 234, 590]
NAV_ITEM_H = 44

# Vertical rhythm shared by every input mode: input area, then Submit, then
# a generously-sized result card - instead of a small card floating in an
# otherwise empty content pane.
INPUT_Y = 24
INPUT_H = 150
SUBMIT_Y = 186
SUBMIT_H = 36
CARD_Y = 240
CARD_H = CONTENT_H - CARD_Y - 24


def is_connected():
    """check for an active internet connection"""
    try:
        # connects to the host and tells us if the host is actually reachable
        socket.create_connection(("1.1.1.1", 53))
        return True
    except OSError:
        pass
    return False


#=========================Main Window=============================
class App:
    def get_theme(self):
        # Cached after first load so background threads (OCR, tweet fetch,
        # voice transcription) can call this without touching the sqlite3
        # connection outside the thread that created it.
        if not hasattr(self, '_theme_cache'):
            self._theme_cache = self.theme_store.load()
        return self._theme_cache

    def apply_theme(self, theme):
        self._theme_cache = theme
        primary, foreground, gray = theme.as_tuple()
        self.master.configure(bg=primary)
        if hasattr(self, 'nav_frame'):
            self.nav_frame.configure(bg=primary)
            self.wordmark.configure(bg=primary, fg=foreground)
            self.nav_divider.configure(bg=gray)

        # Every nav row's command fully rebuilds the top bar + content area
        # from scratch with fresh theme colors, so re-invoking whichever one
        # is active is a simple, robust way to repaint the whole page (it
        # does mean a sub-tab resets to its default on theme change, which is
        # a fine trade for not hand-tracking colors on every widget).
        active = getattr(self, '_active_nav', None)
        btn = self.nav_buttons.get(active) if hasattr(self, 'nav_buttons') else None
        if btn is not None:
            btn.invoke()

    def build_nav_item(self, key, index, icon_path, label, command):
        """One full-width sidebar row: icon + label, highlighted via set_active_nav."""
        primary, foreground, gray = self.get_theme().as_tuple()
        icon = ImageTk.PhotoImage(Image.open(icon_path).resize((22, 22)))
        btn = tk.Button(self.nav_frame, image=icon, text='  ' + label, compound='left',
                         font=('Segoe UI', 10), bd=0, anchor='w', padx=14,
                         bg=primary, fg=gray, activebackground=gray, activeforeground=foreground,
                         command=command)
        btn.image = icon  # keep a reference alive - Tkinter drops GC'd PhotoImages
        btn.place(x=0, y=NAV_ITEM_Y[index], width=RAIL_W, height=NAV_ITEM_H)
        self.nav_buttons[key] = btn
        return btn

    def build_mode_tabs(self, title, on_polarity, on_depression):
        """Page title + a 2-segment pill control (Polarity / Language Patterns).

        Replaces the old sliding-underline-image tab bar that was duplicated
        once per input mode. Created once per mode; polarity()/depression()
        just call set_active_mode() to recolor it instead of rebuilding it."""
        primary, foreground, gray = self.get_theme().as_tuple()
        for w in self.top_frame.winfo_children():
            w.destroy()

        tk.Label(self.top_frame, text=title, font=('Segoe UI', 16, 'bold'), bg=primary, fg=foreground).place(x=0, y=10)

        tabs = tk.Frame(self.top_frame, bg=primary)
        tabs.place(x=0, y=48, width=340, height=36)
        self.pol_btn = tk.Button(tabs, text='Polarity', font=('Segoe UI', 9, 'bold'), bd=0, command=on_polarity)
        self.pol_btn.place(x=0, y=0, width=168, height=36)
        self.dep_btn = tk.Button(tabs, text='Language Patterns', font=('Segoe UI', 9, 'bold'), bd=0, command=on_depression)
        self.dep_btn.place(x=172, y=0, width=168, height=36)

    def set_active_mode(self, mode):
        """mode: 'polarity' or 'depression'. Colors the segmented control built by build_mode_tabs."""
        primary, foreground, gray = self.get_theme().as_tuple()
        self._active_mode = mode
        is_pol = mode == 'polarity'
        self.pol_btn.configure(bg=ACCENT if is_pol else gray, fg=ACCENT_TEXT if is_pol else foreground, activebackground=ACCENT if is_pol else gray)
        self.dep_btn.configure(bg=ACCENT if not is_pol else gray, fg=ACCENT_TEXT if not is_pol else foreground, activebackground=ACCENT if not is_pol else gray)

    def build_result_card(self, parent, ready_detail, x=PAD, y=CARD_Y, width=FIELD_W, height=CARD_H, detail_y=56):
        """Shared modern result card: a title + one detail line. Used as-is for
        depression results, and as the base that build_polarity_card extends
        with percentage bars."""
        primary, foreground, gray = self.get_theme().as_tuple()
        self.result_card = tk.Frame(parent, bg=primary, relief='groove', bd=1)
        self.result_card.place(x=x, y=y, width=width, height=height)
        self.result_title = tk.Label(self.result_card, text='Ready to analyze', font=('Segoe UI', 15, 'bold'), fg=foreground, bg=primary)
        self.result_title.place(x=24, y=20)
        self.result_detail = tk.Label(self.result_card, text=ready_detail, font=('Segoe UI', 10), fg=foreground, bg=primary, wraplength=width - 48, justify='left')
        self.result_detail.place(x=24, y=detail_y)
        return self.result_card

    def render_depression_result(self, is_depressive):
        if is_depressive:
            self.result_title.configure(text='Result: depressive tone detected', fg=NEGATIVE)
            self.result_detail.configure(text="The model leaned toward the depressive class for this input - a word-pattern signal, not a diagnosis.")
        else:
            self.result_title.configure(text='Result: no strong depressive tone detected', fg=POSITIVE)
            self.result_detail.configure(text='The model leaned toward the non-depressive class for this input.')

    def build_polarity_card(self, parent, x=PAD, y=CARD_Y, width=FIELD_W, height=CARD_H):
        """Modern replacement for the old three separate positive/neutral/negative
        boxes: one card with a headline plus a percentage bar per class."""
        primary, foreground, gray = self.get_theme().as_tuple()
        self.build_result_card(parent, "Type something and press Submit to see the breakdown.", x=x, y=y, width=width, height=height, detail_y=52)
        self._polarity_bars = {}
        specs = [('positive', 'Positive', POSITIVE), ('neutral', 'Neutral', NEUTRAL), ('negative', 'Negative', NEGATIVE)]
        bars_top = 100
        row_h = (height - bars_top - 24) // 3
        for i, (key, label, color) in enumerate(specs):
            row_y = bars_top + i * row_h
            lbl = tk.Label(self.result_card, text=label, font=('Segoe UI', 10, 'bold'), fg=foreground, bg=primary)
            lbl.place(x=24, y=row_y + 6, width=90)
            track = tk.Frame(self.result_card, bg=gray)
            track.place(x=120, y=row_y + 8, width=width - 190, height=18)
            fill = tk.Frame(track, bg=color)
            fill.place(x=0, y=0, relwidth=0.0, relheight=1)
            pct_lbl = tk.Label(self.result_card, text='0%', font=('Segoe UI', 10, 'bold'), fg=foreground, bg=primary)
            pct_lbl.place(x=width - 60, y=row_y + 6)
            self._polarity_bars[key] = (fill, pct_lbl)

    def render_polarity_result(self, scores):
        """scores: dict with 'positive'/'neutral'/'negative' -> 0-100 int."""
        colors = {'positive': POSITIVE, 'neutral': NEUTRAL, 'negative': NEGATIVE}
        dominant = max(scores, key=scores.get)
        self.result_title.configure(text=f'Result: mostly {dominant}', fg=colors[dominant])
        self.result_detail.configure(text="Positive / neutral / negative shares from VADER's sentiment score.")
        for key, pct in scores.items():
            fill, pct_lbl = self._polarity_bars[key]
            fill.place_configure(relwidth=pct / 100)
            pct_lbl.configure(text=f'{pct}%')

    def build_voice_ui(self, parent, on_submit):
        """Mic recording UI shared by the voice tab's polarity/depression sub-tabs.

        Records with Extensions.voice.Recorder, transcribes with the free Google
        Web Speech API, then lets the user edit the transcript before running it
        through on_submit (polarity_scorer or depressive_scorer - the same model
        every other input mode uses)."""
        primary, foreground, gray = self.get_theme().as_tuple()

        self.voice_status = tk.Label(parent, text='Press Start Recording and speak, then press Stop.', font=('Segoe UI', 10), fg=foreground, bg=primary)
        self.voice_status.place(x=PAD, y=INPUT_Y + 6)

        self.voice_text_box = tk.Text(parent, font=('Segoe UI', 11), bg=primary, fg=foreground, insertbackground=foreground, relief='groove', bd=1, wrap='word', padx=12, pady=10)
        self.voice_text_box.place(x=PAD, y=INPUT_Y + 40, width=FIELD_W, height=INPUT_H - 40)
        self.voice_text_box.insert(tk.END, 'Your transcribed speech will appear here. Edit it if needed, then press Submit.')

        recorder = voice.Recorder()
        state = {'recording': False}

        def toggle():
            if not state['recording']:
                state['recording'] = True
                self.voice_toggle_btn.configure(text='Stop Recording', bg=NEGATIVE, fg='#ffffff')
                self.voice_status.configure(text='Recording... speak now.')
                recorder.start()
                return

            state['recording'] = False
            self.voice_toggle_btn.configure(text='Start Recording', bg=ACCENT, fg=ACCENT_TEXT, state=tk.DISABLED)
            self.voice_status.configure(text='Transcribing...')

            def work():
                wav_bytes = recorder.stop()
                try:
                    text = voice.transcribe(wav_bytes)
                    self.voice_text_box.delete("1.0", tk.END)
                    self.voice_text_box.insert(tk.END, text)
                    self.voice_status.configure(text='Transcribed - edit if needed, then press Submit.')
                except voice.TranscriptionError as error:
                    self.voice_status.configure(text=str(error))
                finally:
                    self.voice_toggle_btn.configure(state=tk.NORMAL)

            threading.Thread(target=work, daemon=True).start()

        self.voice_toggle_btn = tk.Button(parent, text='Start Recording', font=('Segoe UI', 9, 'bold'), bg=ACCENT, fg=ACCENT_TEXT, bd=0, command=toggle)
        self.voice_toggle_btn.place(x=PAD + FIELD_W - 150, y=INPUT_Y, width=150, height=30)
        hover.Hover(self.voice_toggle_btn)

        def submit():
            content = self.voice_text_box.get("1.0", 'end-1c')
            if not content.strip():
                messagebox.showerror("Entry error", "Record or type something first.")
                return
            on_submit(content)

        self.submit = tk.Button(parent, text='Submit', bg=ACCENT, fg=ACCENT_TEXT, font=('Segoe UI', 9, 'bold'), bd=0, activebackground=ACCENT_HOVER, command=submit)
        self.submit.place(x=PAD + FIELD_W - 110, y=SUBMIT_Y, width=110, height=SUBMIT_H)
        hover.Hover(self.submit)

    def build_upload_dropzone(self, render):
        """File upload UI shared by the File tab's polarity/depression sub-tabs.

        render(content, source) displays the file's text - either
        polarity_widgets or depressive_widgets, bound by the caller."""
        primary, foreground, gray = self.get_theme().as_tuple()
        dropzone_h = SUBMIT_Y + SUBMIT_H - INPUT_Y

        def openfile():
            filepath = filedialog.askopenfilename(
                initialdir='Documents', title='Open a Document',
                filetypes=(("Text Document", "*.txt"), ("PNG Files", "*.png"), ("JPEG Files", "*.jpg")),
            )
            if not filepath:
                return
            suffix = Path(filepath).suffix.lower()
            if suffix == '.txt':
                with open(filepath) as file_:
                    content = file_.read()
                render(content, "document")
            elif suffix in ('.jpg', '.jpeg', '.png'):
                for w in self.main_frame.winfo_children():
                    w.place_forget()
                load_lbl = loading.ImageLabel(self.main_frame, bg=gray)
                load_lbl.place(x=PAD + FIELD_W // 2 - 35, y=CARD_Y, width=70, height=70)

                def clean():
                    if not is_connected():
                        load_lbl.unload()
                        load_lbl.place_forget()
                        lbl_404 = tk.PhotoImage(file='images/error-404.png')
                        tryagain = tk.Button(self.main_frame, image=lbl_404, text='No internet, try again', compound='top',
                                              font=('Segoe UI', 9, 'bold'), bg=gray, activebackground=gray, fg=foreground, bd=0,
                                              command=lambda: self.build_upload_dropzone(render))
                        tryagain.image = lbl_404
                        tryagain.place(x=PAD + FIELD_W // 2 - 90, y=CARD_Y)
                        return
                    try:
                        content = vision.detect_text(filepath)
                    except Exception as error:
                        load_lbl.unload()
                        load_lbl.place_forget()
                        messagebox.showerror("OCR error", f"Could not read text from the image:\n{error}")
                        return
                    load_lbl.unload()
                    load_lbl.place_forget()
                    if content:
                        render(content, "image")
                    else:
                        messagebox.showerror("OCR error", "No text was found in that image.")

                def load():
                    load_lbl.load('images/load.gif')
                threading.Thread(target=clean).start()
                threading.Thread(target=load).start()
            else:
                messagebox.showerror("File Error", "Please choose a .txt, .jpg, or .png file.")

        dropzone = tk.Frame(self.main_frame, bg=primary, width=FIELD_W, height=dropzone_h, relief='groove', bd=1)
        dropzone.place(x=PAD, y=INPUT_Y)

        icon1 = ImageTk.PhotoImage(Image.open('images/image.png').resize((44, 44)))
        icon2 = ImageTk.PhotoImage(Image.open('images/document.png').resize((44, 44)))
        img_lbl = tk.Label(dropzone, bg=primary, image=icon1, bd=0)
        img_lbl.image = icon1
        img_lbl.place(x=FIELD_W // 2 - 52, y=20)
        doc_lbl = tk.Label(dropzone, bg=primary, image=icon2, bd=0)
        doc_lbl.image = icon2
        doc_lbl.place(x=FIELD_W // 2 + 8, y=20)

        tk.Label(dropzone, text='Upload an image or text file', font=('Segoe UI', 11, 'bold'), fg=foreground, bg=primary).place(x=FIELD_W // 2 - 110, y=82, width=220)
        tk.Label(dropzone, text='Images and text files must contain text to extract.', font=('Segoe UI', 9), fg=foreground, bg=primary).place(x=FIELD_W // 2 - 150, y=106, width=300, height=18)

        attach_btn = tk.Button(dropzone, text='Choose Files', font=('Segoe UI', 10, 'bold'), fg=ACCENT_TEXT, bg=ACCENT, activebackground=ACCENT_HOVER, bd=0, command=openfile)
        attach_btn.place(x=FIELD_W // 2 - 70, y=dropzone_h - 55, width=140, height=36)
        hover.Hover(attach_btn)

    def show_loading(self, primary, foreground, callback, delay=3000):
        load_lbl = loading.ImageLabel(self.master, bg=primary)
        load_lbl.place(relx=0.45, rely=0.40, width=70, height=70)
        load_lbl.load('images/load.gif')
        self.loading = tk.Label(self.master, text='Getting things ready...', fg=foreground, bg=primary, font=('normal',9))
        self.loading.place(relx=0.425, rely=0.49)
        self.master.after(delay, callback)

    def __init__(self, master): 
        self.theme_store = ThemeStore(conn)
        theme = self.get_theme()
        primary, foreground, gray = theme.as_tuple()
        
        w = 900 # window width
        h = 650 # window height

        ws = root.winfo_screenwidth() # width of the screen
        hs = root.winfo_screenheight() # height of the screen    

        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2) 

        master.iconbitmap("images/logo_img.ico")
        self.master = master
        self.master.title(APP_NAME)
        self.master.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.master.configure(background=primary)
        self.master.resizable(False,False)

        def getstarted(event=None):
            for widget in self.master.winfo_children():
                widget.destroy()
            def continue_():
                #=============Top Frame (page title + segmented tabs)===========
                self.top_frame = tk.Frame(self.master,width=CONTENT_W,height=HEADER_H,bg=primary,relief='flat',bd=0)
                self.top_frame.place(x=CONTENT_X,y=0)
                #===============Navigation Rail===============
                self.nav_frame = tk.Frame(self.master,bg=primary,width=RAIL_W,height=650,relief='flat',bd=0)
                self.nav_frame.place(x=0,y=0)
                #=============Content Frame=======================
                self.main_frame = tk.Frame(self.master,width=CONTENT_W,height=CONTENT_H,bg=gray)
                self.main_frame.place(x=CONTENT_X,y=CONTENT_Y)

                # Logo + wordmark
                self.logo = ImageTk.PhotoImage(Image.open('images/logo_img.png').resize((30, 30)))
                self.logo_ = tk.Label(self.nav_frame,bg=primary,image=self.logo,bd=0)
                self.logo_.place(x=20,y=18)
                self.wordmark = tk.Label(self.nav_frame,bg=primary,fg=foreground,text=APP_NAME.upper(),font=('Segoe UI',14,'bold'))
                self.wordmark.place(x=58,y=24)
                self.nav_divider = tk.Frame(self.nav_frame,bg=gray,height=1,width=RAIL_W - 32)
                self.nav_divider.place(x=16,y=66)

                # Sliding accent indicator next to whichever nav row is active
                self.nav_indicator = tk.Frame(self.nav_frame,bg=ACCENT,width=4,height=44)
                self.nav_indicator.place(x=0,y=NAV_ITEM_Y[0])

                self.nav_buttons = {}

                def set_active_nav(key):
                    """Highlight the active nav row (and settings) and slide the
                    accent indicator next to it. Re-run after a theme change so
                    every row picks up the new colors."""
                    self._active_nav = key
                    primary, foreground, gray = self.get_theme().as_tuple()
                    for i, item_key in enumerate(NAV_ORDER):
                        btn = self.nav_buttons.get(item_key)
                        if btn is None:
                            continue
                        active = item_key == key
                        btn.configure(bg=gray if active else primary, fg=foreground if active else gray)
                        if active:
                            self.nav_indicator.place_configure(y=NAV_ITEM_Y[i])
                    self.nav_indicator.configure(bg=ACCENT)
                self.set_active_nav = set_active_nav


                def editable_result_widgets(content, source, primary, foreground, gray, on_submit, build_card):
                    """Shared by polarity_widgets/depressive_widgets: an editable text
                    box pre-filled with fetched/uploaded content, a Submit button, and
                    whichever result card the caller asks for."""
                    for widget in self.main_frame.winfo_children():
                        widget.destroy()

                    if source == "twitter":
                        twitter_icon = ImageTk.PhotoImage(Image.open('images/twitter.png').resize((32, 32)))
                        twitter_lbl = tk.Label(self.main_frame,image=twitter_icon,bg=gray,bd=0)
                        twitter_lbl.image = twitter_icon
                        twitter_lbl.place(x=PAD+FIELD_W-40,y=INPUT_Y+4)

                    self.text_box = tk.Text(self.main_frame,font=('Segoe UI',11),bg=primary,fg=foreground,insertbackground=foreground,relief='groove',bd=1,wrap='word',padx=12,pady=10)
                    self.text_box.place(x=PAD,y=INPUT_Y,width=FIELD_W,height=INPUT_H)
                    self.text_box.insert(tk.END,content)
                    def submit():
                        content = self.text_box.get("1.0",'end-1c') # The content of the text box
                        if content == "":
                            messagebox.showerror("Entry error","You can not perform sentiment analysis on an empty text box")
                        else:
                            on_submit(content)
                    self.submit = tk.Button(self.main_frame,text='Submit',bg=ACCENT,fg=ACCENT_TEXT,font=('Segoe UI',9,'bold'),bd=0,activebackground=ACCENT_HOVER,command=submit)
                    self.submit.place(x=PAD+FIELD_W-110,y=SUBMIT_Y,width=110,height=SUBMIT_H)
                    hover.Hover(self.submit)
                    build_card()

                def polarity_widgets(content, source, primary, foreground, gray):
                    """Display fetched/uploaded content with the polarity result card, for document and link sections."""
                    editable_result_widgets(content, source, primary, foreground, gray, polarity_scorer, lambda: self.build_polarity_card(self.main_frame))

                def depressive_widgets(content, source, primary, foreground, gray):
                    """Display fetched/uploaded content with the depression result card, for document and link sections."""
                    editable_result_widgets(content, source, primary, foreground, gray, depressive_scorer, lambda: self.build_result_card(self.main_frame, "Flags word choices statistically associated with depressive language. Not a diagnosis."))

                def polarity_scorer(content):
                    """Run VADER on content and update the shared polarity result card."""
                    result = PolarityScore.sentiment(content) # A dictionary of sentiment scores
                    scores = {
                        'negative': int(result['neg'] * 100),
                        'neutral': int(result['neu'] * 100),
                        'positive': int(result['pos'] * 100),
                    }
                    self.render_polarity_result(scores)
                
                def depressive_scorer(text):
                    """Run the depression-language model on text and update the result card."""
                    try:
                        result = DepressionScore.predict_depressive(text)
                    except Exception as error:
                        messagebox.showerror("Language pattern checker error", f"The model could not be loaded:\n{error}")
                        return
                    self.render_depression_result(result)
                                       
                def text():
                    self.master.title(f"{APP_NAME}  >  Text")
                    self.set_active_nav('text')
                    for w in self.main_frame.winfo_children():
                        w.destroy()

                    #=============Polarity and Depression functions===========
                    def polarity():
                        self.master.title(f"{APP_NAME}  >  Text  >  Polarity")
                        primary, foreground, gray = self.get_theme().as_tuple()
                        self.set_active_mode('polarity')
                        for w in self.main_frame.winfo_children():
                            w.destroy()
                        self.text_box = tk.Text(self.main_frame,font=('Segoe UI',11),bg=primary,fg=foreground,insertbackground=foreground,relief='groove',bd=1,wrap='word',padx=12,pady=10)
                        self.text_box.place(x=PAD,y=INPUT_Y,width=FIELD_W,height=INPUT_H)
                        self.text_box.insert(tk.END,'Type a few sentences here and press Submit to check the tone.')
                        self.text_box.bind("<FocusIn>", lambda args: self.text_box.delete("1.0",tk.END))

                        def submit():
                            content = self.text_box.get("1.0",'end-1c') # The content of the text box
                            if content == "":
                                messagebox.showerror("Entry error","You can not perform sentiment analysis on an empty text box")
                            else:
                                polarity_scorer(content)
                        self.submit = tk.Button(self.main_frame,text='Submit',bg=ACCENT,fg=ACCENT_TEXT,font=('Segoe UI',9,'bold'),bd=0,activebackground=ACCENT_HOVER,command=submit)
                        self.submit.place(x=PAD+FIELD_W-110,y=SUBMIT_Y,width=110,height=SUBMIT_H)
                        hover.Hover(self.submit)
                        self.build_polarity_card(self.main_frame)

                    def depression():
                        self.master.title(f"{APP_NAME}  >  Text  >  Depression")
                        primary, foreground, gray = self.get_theme().as_tuple()
                        self.set_active_mode('depression')
                        for w in self.main_frame.winfo_children():
                            w.destroy()
                        self.text_box = tk.Text(self.main_frame,font=('Segoe UI',11),bg=primary,fg=foreground,insertbackground=foreground,relief='groove',bd=1,wrap='word',padx=12,pady=10)
                        self.text_box.place(x=PAD,y=INPUT_Y,width=FIELD_W,height=INPUT_H)
                        self.text_box.insert(tk.END,'Type a few sentences here and press Submit to check the tone.')
                        self.text_box.bind("<FocusIn>", lambda args: self.text_box.delete("1.0",tk.END))

                        def submit():
                            content = self.text_box.get("1.0",'end-1c') # The content of the text box
                            if not content.strip():
                                messagebox.showerror("Entry error","You can not perform sentiment analysis on an empty text box")
                            else:
                                depressive_scorer(content)
                        self.submit = tk.Button(self.main_frame,text='Submit',bg=ACCENT,fg=ACCENT_TEXT,font=('Segoe UI',9,'bold'),bd=0,activebackground=ACCENT_HOVER,command=submit)
                        self.submit.place(x=PAD+FIELD_W-110,y=SUBMIT_Y,width=110,height=SUBMIT_H)
                        hover.Hover(self.submit)
                        self.build_result_card(self.main_frame, "Flags word choices statistically associated with depressive language. Not a diagnosis.")

                    self.build_mode_tabs('Text', polarity, depression)
                    polarity() # Run the polarity function on start
                # Text Button
                self.build_nav_item('text', 0, 'images/text_img.png', 'Type Text', text)
                def doc():
                    self.master.title(f"{APP_NAME}  >  File")
                    self.set_active_nav('doc')
                    for w in self.main_frame.winfo_children():
                        w.destroy()
                    #=============Polarity and Depression functions===========
                    def polarity():
                        self.master.title(f"{APP_NAME}  >  File  >  Polarity")
                        self.set_active_mode('polarity')
                        for w in self.main_frame.winfo_children():
                            w.destroy()
                        self.build_upload_dropzone(lambda content, source: polarity_widgets(content, source, *self.get_theme().as_tuple()))
                        self.build_polarity_card(self.main_frame)

                    def depression():
                        self.master.title(f"{APP_NAME}  >  File  >  Depression")
                        self.set_active_mode('depression')
                        for w in self.main_frame.winfo_children():
                            w.destroy()
                        self.build_upload_dropzone(lambda content, source: depressive_widgets(content, source, *self.get_theme().as_tuple()))
                        self.build_result_card(self.main_frame, "Flags word choices statistically associated with depressive language. Not a diagnosis.")

                    self.build_mode_tabs('File', polarity, depression)
                    polarity() # Run the polarity function on start
                # Attach Document Button
                self.build_nav_item('doc', 1, 'images/doc_img.png', 'Upload File', doc)
                def voice():
                    self.master.title(f"{APP_NAME}  >  Voice Record")
                    self.set_active_nav('voice')
                    for w in self.main_frame.winfo_children():
                        w.destroy()
                    #=============Polarity and Depression functions===========
                    def polarity():
                        self.master.title(f"{APP_NAME}  >  Voice Record  >  Polarity")
                        self.set_active_mode('polarity')
                        for w in self.main_frame.winfo_children():
                            w.destroy()
                        self.build_voice_ui(self.main_frame, polarity_scorer)
                        self.build_polarity_card(self.main_frame)

                    def depression():
                        self.master.title(f"{APP_NAME}  >  Voice Record  >  Depression")
                        self.set_active_mode('depression')
                        for w in self.main_frame.winfo_children():
                            w.destroy()
                        self.build_voice_ui(self.main_frame, depressive_scorer)
                        self.build_result_card(self.main_frame, "Flags word choices statistically associated with depressive language. Not a diagnosis.")

                    self.build_mode_tabs('Voice Recording', polarity, depression)
                    polarity() # Run the polarity function on start
                # Voice Record Button
                self.build_nav_item('voice', 2, 'images/voice_img.png', 'Voice Record', voice)
                def link():
                    self.master.title(f"{APP_NAME}  >  Social Media Post")
                    self.set_active_nav('link')
                    for w in self.main_frame.winfo_children():
                        w.destroy()

                    def link_widgets(render):
                        """widgets for the link section. render(content, source) displays
                        the fetched post text - either polarity_widgets or depressive_widgets,
                        bound by the caller so this doesn't need to guess which tab is active."""
                        primary, foreground, gray = self.get_theme().as_tuple()
                        self.url_ent = tk.Entry(self.main_frame,font=('Segoe UI',10),fg='gray60',insertbackground=foreground,bg=primary,relief='groove',bd=1)
                        self.url_ent.place(x=PAD,y=INPUT_Y,width=FIELD_W-120,height=36)
                        self.url_ent.insert(tk.END,'Enter a public X (Twitter) post URL...')
                        self.url_ent.bind("<FocusIn>", lambda args: (self.url_ent.delete("0",tk.END),self.url_ent.configure(fg=foreground)))
                        self.url_ent.bind("<FocusOut>", lambda args: (self.url_ent.insert(tk.END,'Enter a public X (Twitter) post URL...'),self.url_ent.configure(fg='gray60')))

                        def search():
                            url = self.url_ent.get()

                            if not validators.url(url) or not any(domain in url for domain in ("twitter.com", "x.com")):
                                messagebox.showerror("Url Error", "Enter a public X (Twitter) post URL, e.g. https://x.com/user/status/12345")
                                return

                            for w in self.main_frame.winfo_children():
                                w.destroy()
                            source = "twitter"
                            load_lbl = loading.ImageLabel(self.main_frame,bg=gray)
                            load_lbl.place(x=PAD+FIELD_W//2-35,y=CARD_Y,width=70,height=70)
                            def get_post():
                                try:
                                    content = twitter.get_text(url) # fetched via the public oEmbed API, no login/keys needed
                                except twitter.TweetFetchError as error:
                                    load_lbl.unload()
                                    load_lbl.place_forget()
                                    messagebox.showerror("Post fetch error", str(error))
                                    return
                                load_lbl.unload()
                                render(content, source)
                            def load():
                                load_lbl.load('images/load.gif')
                            threading.Thread(target=get_post).start()
                            threading.Thread(target=load).start()
                        self.submit = tk.Button(self.main_frame,text='Search',bg=ACCENT,fg=ACCENT_TEXT,font=('Segoe UI',9,'bold'),bd=0,activebackground=ACCENT_HOVER,command=search)
                        self.submit.place(x=PAD+FIELD_W-110,y=INPUT_Y,width=110,height=36)
                        hover.Hover(self.submit)
                        self.main_frame.bind("<Return>",search)

                    #=============Polarity and Depression functions===========
                    def polarity():
                        self.set_active_mode('polarity')
                        for w in self.main_frame.winfo_children():
                            w.destroy()
                        primary, foreground, gray = self.get_theme().as_tuple()
                        load_lbl = loading.ImageLabel(self.main_frame,bg=gray)
                        load_lbl.place(x=PAD+FIELD_W//2-35,y=CARD_Y,width=70,height=70)
                        def check_connection():
                            if is_connected(): # If there is internet connection
                                load_lbl.unload()
                                link_widgets(lambda content, source: polarity_widgets(content, source, *self.get_theme().as_tuple()))
                                self.master.title(f"{APP_NAME}  >  Social Media Post  >  Polarity")
                            else:
                                load_lbl.unload()
                                lbl_404 = tk.PhotoImage(file='images/error-404.png')
                                tryagain = tk.Button(self.main_frame,image=lbl_404,text='No internet, try again',compound='top',font=('Segoe UI',9,'bold'),bg=gray,activebackground=gray,fg=foreground,bd=0,command=link)
                                tryagain.image = lbl_404
                                tryagain.place(x=PAD+FIELD_W//2-90,y=CARD_Y)
                        def load():
                            load_lbl.load('images/load.gif')
                        threading.Thread(target=check_connection).start()
                        threading.Thread(target=load).start()

                    def depression():
                        self.set_active_mode('depression')
                        for w in self.main_frame.winfo_children():
                            w.destroy()
                        primary, foreground, gray = self.get_theme().as_tuple()
                        load_lbl = loading.ImageLabel(self.main_frame,bg=gray)
                        load_lbl.place(x=PAD+FIELD_W//2-35,y=CARD_Y,width=70,height=70)
                        def check_connection():
                            if is_connected(): # If there is internet connection
                                load_lbl.unload()
                                link_widgets(lambda content, source: depressive_widgets(content, source, *self.get_theme().as_tuple()))
                                self.master.title(f"{APP_NAME}  >  Social Media Post  >  Depression")
                            else:
                                load_lbl.unload()
                                lbl_404 = tk.PhotoImage(file='images/error-404.png')
                                tryagain = tk.Button(self.main_frame,image=lbl_404,text='No internet, try again',compound='top',font=('Segoe UI',9,'bold'),bg=gray,activebackground=gray,fg=foreground,bd=0,command=link)
                                tryagain.image = lbl_404
                                tryagain.place(x=PAD+FIELD_W//2-90,y=CARD_Y)
                        def load():
                            load_lbl.load('images/load.gif')
                        threading.Thread(target=check_connection).start()
                        threading.Thread(target=load).start()

                    self.build_mode_tabs('Social Post', polarity, depression)
                    polarity() # Run the polarity function
                # Social media link Button
                self.build_nav_item('link', 3, 'images/link_img.png', 'Social Post', link)

                def settings():
                    self.master.title(f"{APP_NAME}  >  Settings")
                    self.set_active_nav('settings')
                    primary, foreground, gray = self.get_theme().as_tuple()
                    for w in self.main_frame.winfo_children():
                        w.destroy()
                    for w in self.top_frame.winfo_children():
                        w.destroy()

                    tk.Label(self.top_frame,text='Settings',font=('Segoe UI',16,'bold'),bg=primary,fg=foreground).place(x=0,y=10)

                    notif_img = ImageTk.PhotoImage(Image.open('images/notification.png').resize((22,22)))
                    self.notif_lbl = tk.Label(self.main_frame,text='  Notifications',font=('Segoe UI',11,'bold'),image=notif_img,compound='left',bg=gray,fg=foreground)
                    self.notif_lbl.image = notif_img
                    self.notif_lbl.place(x=PAD,y=INPUT_Y)

                    self.notification = tk.Frame(self.main_frame,bg=primary,relief='groove',bd=1)
                    self.notification.place(x=PAD,y=INPUT_Y+36,width=FIELD_W,height=150)
                    self.lbl1 = tk.Label(self.notification,text='Notify me when...',font=('Segoe UI',10,'bold'),bg=primary,fg=foreground)
                    self.lbl1.place(relx=0.04,rely=0.06)
                    w = tk.IntVar()
                    x = tk.IntVar()
                    y = tk.IntVar()
                    z = tk.IntVar()
                    self.predictionsmade = tk.Checkbutton(self.notification,text='Predictions have been made',bg=primary,fg=foreground,activebackground=primary,selectcolor=primary,font=("Segoe UI",10),onvalue=1,offvalue=0,variable=w)
                    self.predictionsmade.place(relx=0.04,rely=0.26)
                    self.newmodel = tk.Checkbutton(self.notification,text='New model available',bg=primary,fg=foreground,activebackground=primary,selectcolor=primary,font=("Segoe UI",10),onvalue=1,offvalue=0,variable=x)
                    self.newmodel.place(relx=0.04,rely=0.46)
                    self.visulization = tk.Checkbutton(self.notification,text='Visualizations have been plotted',bg=primary,fg=foreground,selectcolor=primary,activebackground=primary,font=("Segoe UI",10),onvalue=1,offvalue=0,variable=y)
                    self.visulization.place(relx=0.04,rely=0.66)
                    self.nothing = tk.Checkbutton(self.notification,text='Nothing',bg=primary,fg=foreground,activebackground=primary,selectcolor=primary,font=("Segoe UI",10),onvalue=1,offvalue=0,variable=z)
                    self.nothing.place(relx=0.04,rely=0.86)

                    theme_img = ImageTk.PhotoImage(Image.open('images/theme.png').resize((22,22)))
                    self.theme_lbl = tk.Label(self.main_frame,text='  Appearance',font=('Segoe UI',11,'bold'),image=theme_img,compound='left',bg=gray,fg=foreground)
                    self.theme_lbl.image = theme_img
                    self.theme_lbl.place(x=PAD,y=INPUT_Y+36+150+20)

                    self.prefrences = tk.Frame(self.main_frame,bg=primary,relief='groove',bd=1)
                    self.prefrences.place(x=PAD,y=INPUT_Y+36+150+56,width=FIELD_W,height=CONTENT_H-(INPUT_Y+36+150+56)-16)

                    self.lbl2 = tk.Label(self.prefrences,text='How should I look?',font=('Segoe UI',10,'bold'),bg=primary,fg=foreground)
                    self.lbl2.place(relx=0.04,rely=0.08)
                    self.light_img = ImageTk.PhotoImage(Image.open('images/light.png').resize((90,90)))
                    self.dark_img = ImageTk.PhotoImage(Image.open('images/dark.png').resize((90,90)))

                    def dark():
                        if self.nav_frame['background'] == '#ffffff': # That means we are on light mode
                            theme = self.theme_store.set_mode('dark')
                            self.apply_theme(theme)
                        else:
                            pass

                    def light():
                        if self.nav_frame['background'] == '#181818': # That means we are on light mode
                            theme = self.theme_store.set_mode('light')
                            self.apply_theme(theme)
                        else:
                            pass

                    self.selection = tk.StringVar()
                    if primary == '#ffffff':
                        self.selection.set("light")
                    else:
                        self.selection.set("dark")
                    self.light = tk.Radiobutton(self.prefrences,text='Light',image=self.light_img,bg=primary,fg=foreground,activebackground=primary,selectcolor=primary,compound='top',font=("Segoe UI",10),value="light",variable=self.selection,command=light)
                    self.dark = tk.Radiobutton(self.prefrences,text='Dark',image=self.dark_img,bg=primary,fg=foreground,activebackground=primary,selectcolor=primary,compound='top',font=("Segoe UI",10),value="dark",variable=self.selection,command=dark)
                    self.light.place(relx=0.15,rely=0.28)
                    self.dark.place(relx=0.55,rely=0.28)

                self.build_nav_item('settings', 4, 'images/settings.png', 'Settings', settings)

                text() # Run the text function on start
              
            self.show_loading(primary, foreground, continue_)
        # Home Page
        self.bg_img = tk.PhotoImage(file='images/bg.png')
        self.bg = tk.Label(self.master,image=self.bg_img,bg=primary)
        self.bg.place(relx=0,rely=0)
        self.ill_img = tk.PhotoImage(file='images/home_illustration.png')
        self.illustration = tk.Label(self.master,image=self.ill_img,bg=primary)
        self.illustration.place(relx=0.35,rely=0.2)
        self.sentiment_lbl = tk.Label(self.master,text=LANDING_TITLE,fg=foreground,bg=primary,font=('Constantia',35,'bold'))
        self.sentiment_lbl.place(x=36,y=163)
        self.sentiment_info = tk.Label(self.master,text='\n'.join(LANDING_LINES),fg=foreground,bg=primary,font=('Segoe UI',12),justify='left')
        self.sentiment_info.place(x=36,y=232)

        # Get Started Button
        self.getstarted = tk.Button(self.master,text='Get Started',font=('Segoe UI',10,'bold'),fg=ACCENT_TEXT,bg=ACCENT,activebackground=primary,bd=0,command=getstarted)
        self.getstarted.place(x=36,y=364,width=150,height=38)
        self.getstarted.focus() # Focus on this button when the program starts
        hover.Hover(self.getstarted)
        self.getstarted.bind("<Return>",getstarted) # Bind the return(enter) key to the get started function"""

if __name__=='__main__':
    root = tk.Tk() 
    
    conn = sqlite3.connect("Data/Data.db")
    c = conn.cursor() 

    imagescount = len(glob.glob('images/*png')) + len(glob.glob('images/*ico')) + len(glob.glob('images/*gif'))
    if imagescount != 24:
        messagebox.showerror("File Error",str(24-imagescount)+" File(s) missing from images")
    else:
        pass

    app = App(root)
    
    root.mainloop()