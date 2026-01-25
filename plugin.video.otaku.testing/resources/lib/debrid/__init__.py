import threading

from copy import deepcopy
from resources.lib.debrid import premiumize, torbox, easydebrid, real_debrid
from resources.lib.ui import control, client


class Debrid:
    def __init__(self):
        self.premiumizeCached = []
        self.torboxCached = []
        self.easydebridCached = []
        self.realdebridCached = []
        self.alldebridCached = []
        self.debridlinkCached = []

        self.premiumizeUnCached = []
        self.realdebridUnCached = []
        self.alldebridUnCached = []
        self.debridlinkUnCached = []
        self.torboxUnCached = []
        self.threads = []

    def torrentCacheCheck(self, torrent_list):
        enabled_debrids = control.enabled_debrid()
        if enabled_debrids['realdebrid']:
            t = threading.Thread(target=self.real_debrid_worker, args=(deepcopy(torrent_list),))
            t.start()
            self.threads.append(t)

        if enabled_debrids['debridlink']:
            t = threading.Thread(target=self.debrid_link_worker, args=(deepcopy(torrent_list),))
            self.threads.append(t)
            t.start()

        if enabled_debrids['premiumize']:
            t = threading.Thread(target=self.premiumize_worker, args=(deepcopy(torrent_list),))
            t.start()
            self.threads.append(t)

        if enabled_debrids['alldebrid']:
            t = threading.Thread(target=self.all_debrid_worker, args=(deepcopy(torrent_list),))
            t.start()
            self.threads.append(t)

        if enabled_debrids['torbox']:
            t = threading.Thread(target=self.torbox_worker, args=(deepcopy(torrent_list),))
            t.start()
            self.threads.append(t)

        if enabled_debrids['easydebrid']:
            t = threading.Thread(target=self.easydebrid_worker, args=(deepcopy(torrent_list),))
            t.start()
            self.threads.append(t)

        for i in self.threads:
            i.join(timeout=10)  # 10 second max per provider

        # Log if any threads are still running
        still_running = [t for t in self.threads if t.is_alive()]
        if still_running:
            control.log(f'Debrid cache check: {len(still_running)} providers timed out', 'warning')

        cached_list = self.premiumizeCached + self.torboxCached + self.easydebridCached + self.realdebridCached + self.alldebridCached + self.debridlinkCached
        uncached_list = self.realdebridUnCached + self.premiumizeUnCached + self.alldebridUnCached + self.debridlinkUnCached + self.torboxUnCached
        return cached_list, uncached_list

    def all_debrid_worker(self, torrent_list):
        if len(torrent_list) > 0:
            from resources.lib.debrid import all_debrid
            api = all_debrid.AllDebrid()
            magnets = [f"magnet:?xt=urn:btih:{t['hash']}" for t in torrent_list]

            try:
                cache_status = api.check_instant_availability(magnets)
                for torrent in torrent_list:
                    torrent['debrid_provider'] = 'Alldebrid'
                    if cache_status.get(torrent['hash'].lower()):
                        self.alldebridCached.append(torrent)
                    else:
                        self.alldebridUnCached.append(torrent)
            except Exception as e:
                control.log(f'AllDebrid cache check failed: {e}', 'warning')
                for torrent in torrent_list:
                    torrent['debrid_provider'] = 'Alldebrid'
                    self.alldebridUnCached.append(torrent)

    def debrid_link_worker(self, torrent_list):
        hash_list = [i['hash'] for i in torrent_list]
        if len(hash_list) > 0:
            from resources.lib.debrid import debrid_link
            api = debrid_link.DebridLink()

            try:
                cache_status = api.check_instant_availability(hash_list)
                for torrent in torrent_list:
                    torrent['debrid_provider'] = 'Debrid-Link'
                    if cache_status.get(torrent['hash'].lower()):
                        self.debridlinkCached.append(torrent)
                    else:
                        self.debridlinkUnCached.append(torrent)
            except Exception as e:
                control.log(f'Debrid-Link cache check failed: {e}', 'warning')
                for torrent in torrent_list:
                    torrent['debrid_provider'] = 'Debrid-Link'
                    self.debridlinkUnCached.append(torrent)

    def real_debrid_worker(self, torrent_list):
        hash_list = [i['hash'] for i in torrent_list]
        if len(hash_list) > 0:
            api = real_debrid.RealDebrid()
            hash_string = '/'.join(hash_list)
            response = client.get(f'{api.BaseUrl}/torrents/instantAvailability/{hash_string}', headers=api.headers())
            if response and response.ok:
                try:
                    availability = response.json()
                    for torrent in torrent_list:
                        torrent['debrid_provider'] = 'Real-Debrid'
                        torrent_hash = torrent['hash'].lower()
                        # Check if hash exists in response and has available variants
                        if torrent_hash in availability and availability[torrent_hash].get('rd'):
                            self.realdebridCached.append(torrent)
                        else:
                            self.realdebridUnCached.append(torrent)
                except (ValueError, KeyError):
                    # On error, mark all as uncached
                    for torrent in torrent_list:
                        torrent['debrid_provider'] = 'Real-Debrid'
                        self.realdebridUnCached.append(torrent)
            else:
                # API failed, mark all as uncached
                for torrent in torrent_list:
                    torrent['debrid_provider'] = 'Real-Debrid'
                    self.realdebridUnCached.append(torrent)

    def premiumize_worker(self, torrent_list):
        hash_list = [i['hash'] for i in torrent_list]
        if len(hash_list) > 0:
            premiumizeCache = premiumize.Premiumize().hash_check(hash_list)
            premiumizeCache = premiumizeCache['response']

            for index, torrent in enumerate(torrent_list):
                torrent['debrid_provider'] = 'Premiumize'
                if premiumizeCache[index] is True:
                    self.premiumizeCached.append(torrent)
                else:
                    self.premiumizeUnCached.append(torrent)

    def torbox_worker(self, torrent_list):
        hash_list = [i['hash'] for i in torrent_list]
        if len(hash_list) > 0:
            cache_check = [i['hash'] for i in torbox.TorBox().hash_check(hash_list)]
            for torrent in torrent_list:
                torrent['debrid_provider'] = 'TorBox'
                if torrent['hash'] in cache_check:
                    self.torboxCached.append(torrent)
                else:
                    self.torboxUnCached.append(torrent)

    def easydebrid_worker(self, torrent_list):
        # Prepend the magnet prefix to each hash within torrent_list
        hash_list = ["magnet:?xt=urn:btih:" + i['hash'] for i in torrent_list]
        if len(hash_list) > 0:
            response = easydebrid.EasyDebrid().lookup_link(hash_list)
            cached_flags = response.get("cached", [])
            for torrent, is_cached in zip(torrent_list, cached_flags):
                torrent['debrid_provider'] = 'EasyDebrid'
                if is_cached:
                    self.easydebridCached.append(torrent)
