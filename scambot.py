import urllib.request
import json
import re
import tkinter as tk
from tkinter import ttk
import threading
import queue
import winsound

currency_abbreviated = ['alt', 'fuse', 'alch', 'chaos', 'gcp', 'exa', 'chrom', 'jew', 'chance', 'chisel', 'scour', 'blessed', 'regret', 'regal', 'divine', 'vaal']
currency_singular = ['Orb of Alteration', 'Orb of Fusing', 'Orb of Alchemy', 'Chaos Orb', 'Gemcutter\'s Prism', 'Exalted Orb', 'Chromatic Orb', 'Jeweller\'s Orb', 'Orb of Chance', 'Cartographer\'s Chisel', 'Orb of Scouring', 'Blessed Orb', 'Orb of Regret', 'Regal Orb', 'Divine Orb', 'Vaal Orb']
currency_plural = ['Orbs of Alteration', 'Orbs of Fusing', 'Orbs of Alchemy', 'Chaos Orbs', 'Gemcutter\'s Prisms', 'Exalted Orbs', 'Chromatic Orbs', 'Jeweller\'s Orbs', 'Orbs of Chance', 'Cartographer\'s Chisels', 'Orbs of Scouring', 'Blessed Orbs', 'Orbs of Regret', 'Regal Orbs', 'Divine Orbs', 'Vaal Orbs']

price_regex = re.compile('~(b/o|price) ([0-9]+) (alt|fuse|alch|chaos|gcp|exa|chrom|jew|chance|chisel|scour|blessed|regret|regal|divine|vaal)')

stash_api = 'http://pathofexile.com/api/public-stash-tabs?id='

class BeepThread(threading.Thread):
    def __init__(self, spawner):
        threading.Thread.__init__(self)
        self.spawner = spawner
        self.dead = False
        self.start()
        
    def run(self):
        winsound.Beep(440, 1000)
        self.spawner.subthreads.remove(self)
    
    def kill(self):
        self.dead = True

class ParserThread(threading.Thread):
    def __init__(self, spawner, parse_id, league, terms):
        threading.Thread.__init__(self)
        self.dead = False
        self.spawner = spawner
        self.parse_id = parse_id
        self.league = league
        self.terms = terms
        self.start()
        
    def get_stashes(self):
        stash_data = json.loads(urllib.request.urlopen(stash_api + self.parse_id).read())
        self.spawner.queue_parse_ids.put(stash_data['next_change_id'])
        # self.spawner.parse_id.set(stash_data['next_change_id'])
        self.stashes = stash_data['stashes']
    
    def parse_stashes(self):
        for stash in self.stashes:
            for item in stash['items']:
                if item['league'] == self.league:
                    for term in self.terms.split(', '):
                        if self.dead:
                            print('dead')
                            return
                        if term.lower() in item['name'].lower():
                            price_regex_match = price_regex.match(stash['stash'])
                            try:
                                price_regex_match = price_regex.match(item['note'])
                            except KeyError:
                                pass
                            if price_regex_match:
                                self.spawner.queue_results.put({'name':stash['lastCharacterName'], 'item':item['name'][28:],
                                                                'price':price_regex_match, 'league':item['league'],
                                                                'stash':stash['stash'], 'x':item['x'], 'y':item['y']})
        
    def run(self):
        self.get_stashes()
        self.parse_stashes()
        self.spawner.subthreads.remove(self)
    
    def kill(self):
        self.dead = True

class App(tk.Tk):

    def __init__(self):
        tk.Tk.__init__(self)
        self.title('PoE Stash Searcher')
        self.geometry('800x375+900+200')
        self.resizable(False, False)
        self.protocol('WM_DELETE_WINDOW', self.kill)
        self.make_topmost()
        
        self.subthreads = []
        self.queue_results = queue.Queue()
        self.queue_parse_ids = queue.Queue()
        self.start = False
        self.dead = False
        
        self.parse_id_old = ''
        self.parse_id = tk.StringVar()
        self.league = tk.StringVar()
        self.maxprice = tk.DoubleVar()
        self.minprice = tk.DoubleVar()
        self.currency = tk.StringVar()
        self.terms = tk.StringVar()
        
        self.create_search_results()
        self.create_label_parse_id()
        self.create_option_parse_id()
        self.create_label_league()
        self.create_option_league()
        self.create_label_maxprice()
        self.create_option_maxprice()
        self.create_option_currency()
        self.create_label_minprice()
        self.create_option_minprice()
        self.create_label_terms()
        self.create_option_terms()
        self.create_button_start()
        self.create_button_stop()
        
        self.after(500, self.check_queue)

    def create_search_results(self):
        self.results_frame = ttk.Frame(self)
        self.results_frame.grid(row=0, column=0, rowspan=15, columnspan=8, padx=5, pady=5)
        
        self.results_text = tk.Text(self.results_frame, height=20, width=76)
        self.results_text.grid(row=0, column=0)
        self.results_text.configure(state='disabled')
        
        self.results_scroll = tk.Scrollbar(self.results_frame, command=self.results_text.yview)
        self.results_scroll.grid(row=0, column=1, sticky=tk.N+tk.S)
        
        self.results_text['yscrollcommand'] = self.results_scroll.set
        
    def create_label_parse_id(self):
        self.label_parse_id = ttk.Label(self, text='Parse ID')
        self.label_parse_id.grid(row=0, column=8, columnspan=2, padx=5, pady=1, sticky=tk.W)
        
    def create_option_parse_id(self):
        self.option_parse_id = ttk.Entry(self, textvariable=self.parse_id, width=23)
        self.option_parse_id.grid(row=1, column=8, columnspan=2, padx=5, pady=1)
        
    def create_label_league(self):
        self.label_league = ttk.Label(self, text='League')
        self.label_league.grid(row=2, column=8, columnspan=2, padx=5, pady=1, sticky=tk.W)
        
    def create_option_league(self):
        self.option_league = ttk.Combobox(self, textvariable=self.league, state='readonly', width=20)
        self.option_league.grid(row=3, column=8, columnspan=2, padx=5, pady=1)
        self.option_league['values'] = ['Legacy', 'Hardcore Legacy', 'Standard', 'Hardcore']
        self.option_league.current(0)
        
    def create_label_maxprice(self):
        self.label_maxprice = ttk.Label(self, text='Maximum Price')
        self.label_maxprice.grid(row=4, column=8, columnspan=2, padx=5, pady=1, sticky=tk.W)
        
    def create_option_maxprice(self):
        self.option_maxprice = ttk.Entry(self, textvariable=self.maxprice, width=10)
        self.option_maxprice.grid(row=5, column=8, padx=5, pady=1)
        self.option_maxprice.delete(0, tk.END)
        self.option_maxprice.insert(0, '20')
        
    def create_label_minprice(self):
        self.label_minprice = ttk.Label(self, text='Minimum Price')
        self.label_minprice.grid(row=6, column=8, columnspan=2, padx=5, pady=1, sticky=tk.W)
        
    def create_option_minprice(self):
        self.option_minprice = ttk.Entry(self, textvariable=self.minprice, width=10)
        self.option_minprice.grid(row=7, column=8, padx=5, pady=1)
        self.option_minprice.delete(0, tk.END)
        self.option_minprice.insert(0, '1')
        
    def create_option_currency(self):
        self.option_currency = []
        self.option_currency.append(ttk.Combobox(self, textvariable=self.currency, state='readonly', width=7))
        self.option_currency[0].grid(row=5, column=9, padx=5, pady=1)
        self.option_currency[0]['values'] = currency_abbreviated
        self.option_currency[0].current(3)
        
        self.option_currency.append(ttk.Combobox(self, textvariable=self.currency, state='readonly', width=7))
        self.option_currency[1].grid(row=7, column=9, padx=5, pady=1)
        self.option_currency[1]['values'] = currency_abbreviated
        self.option_currency[1].current(3)
        
    def create_label_terms(self):
        self.lable_terms = ttk.Label(self, text='Search Terms')
        self.lable_terms.grid(row=15, column=0, padx=5, pady=5)
        
    def create_option_terms(self):
        self.option_terms = ttk.Entry(self, textvariable=self.terms, width=75)
        self.option_terms.grid(row=15, column=1, columnspan=7, padx=5, pady=5, sticky=tk.W)
        
    def create_button_start(self):
        self.button_start = ttk.Button(self, text='Start', command=self.start_parsing, width=9)
        self.button_start.grid(row=15, column=8, padx=5, pady=5)
        
    def create_button_stop(self):
        self.button_stop = ttk.Button(self, text='Stop', command=self.stop_parsing, state='disabled', width=9)
        self.button_stop.grid(row=15, column=9, padx=5, pady=5)

    def make_topmost(self):
        self.lift()
        self.attributes('-topmost', 1)
        self.attributes('-topmost', 0)
        
    def kill(self):
        self.protocol('WM_DELETE_WINDOW', None)
        self.dead = True
        self.button_start.configure(state='disabled')
        self.button_stop.configure(state='disabled')
        self.option_parse_id.configure(state='disabled')
        self.option_league.configure(state='disabled')
        self.option_maxprice.configure(state='disabled')
        self.option_minprice.configure(state='disabled')
        self.option_currency[0].configure(state='disabled')
        self.option_currency[1].configure(state='disabled')
        self.option_terms.configure(state='disabled')
        for thread in self.subthreads:
            thread.kill()
        self.kill_loop()
        
    def kill_loop(self):
        if len(self.subthreads) == 0:
            self.destroy()
        else:
            self.print_results('Waiting for subthreads to terminate...\n\n')
        self.after(2000, self.kill_loop)
                
        
    def start_parsing(self):
        self.results_text.configure(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.configure(state='disabled')
        self.button_start.configure(state='disabled')
        self.button_stop.configure(state='normal')
        self.option_parse_id.configure(state='disabled')
        self.option_league.configure(state='disabled')
        self.option_maxprice.configure(state='disabled')
        self.option_minprice.configure(state='disabled')
        self.option_currency[0].configure(state='disabled')
        self.option_currency[1].configure(state='disabled')
        self.option_terms.configure(state='disabled')
        self.print_results('Starting search...\n\n')
        self.start = True
        self.queue_parse_ids.put(self.parse_id.get())
        self.parse_stash_data()
        
    def stop_parsing(self):
        self.button_start.configure(state='normal')
        self.button_stop.configure(state='disabled')
        self.option_parse_id.configure(state='normal')
        self.option_league.configure(state='normal')
        self.option_maxprice.configure(state='normal')
        self.option_minprice.configure(state='normal')
        self.option_currency[0].configure(state='normal')
        self.option_currency[1].configure(state='normal')
        self.option_terms.configure(state='normal')
        self.print_results('Stopping search...\n\n')
        self.start = False
        
    def parse_stash_data(self):
        if self.start and not self.dead:
            parse_id = None
            while not self.queue_parse_ids.empty():
                parse_id = self.queue_parse_ids.get()
            if parse_id is not None:
                self.print_results('Parsing ' + parse_id + '...\n\n')
                self.subthreads.append(ParserThread(self, parse_id, self.league.get(), self.terms.get()))
                self.parse_id.set(parse_id)
            self.after(500, self.parse_stash_data)

    def parse_price(self, to_parse):
        price = round(float(to_parse[0]), 1)
        if price == 1.0:
            return str(price) + ' ' + currency_singular[currency_abbreviated.index(to_parse[1])]
        else:
            return str(price) + ' ' + currency_plural[currency_abbreviated.index(to_parse[1])]

    def check_queue(self):
        if not self.queue_results.empty():
            sale = self.queue_results.get()
            if sale['price'].group(3) == self.currency.get() \
               and float(sale['price'].group(2)) <= self.maxprice.get() \
               and float(sale['price'].group(2)) >= self.minprice.get():
                results = '@' + sale['name'] + ' Hi, I would like to buy your ' + sale['item'] + ' listed for ' \
                          + self.parse_price(sale['price'].group(2, 3)) + ' in ' + sale['league'] \
                          + ' (stash tab \"' + sale['stash'] + '\"; position: left ' + str(sale['x']) + ', top ' \
                          + str(sale['y']) + ')'
                self.copy_results(results)
                self.print_results('Found result:\n' + results + '\n\n')
                self.subthreads.append(BeepThread(self))
        self.after(500, self.check_queue)
        
    def print_results(self, string):
        scroll = (self.results_scroll.get()[1] == 1.0)
        self.results_text.configure(state='normal')
        self.results_text.insert(tk.END, string)
        if scroll:
            self.results_text.see(tk.END)
        self.results_text.configure(state='disabled')
            
    def copy_results(self, string):
        self.clipboard_clear()
        self.clipboard_append(string)
            
if __name__ == '__main__':
    App().mainloop()