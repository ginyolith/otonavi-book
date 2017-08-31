import scrapelib
from bs4 import BeautifulSoup
from abc import ABCMeta, abstractmethod
import re


class ScrapingBase(metaclass=ABCMeta):
    '''
    スクレイピングの抽象クラス
    このクラスを継承して、各Webサイト専用の処理を実装する
    '''

    def __init__(self):
        '''
        初期化処理
        引数targetUrlに対象サイトのトップページのURLを入れる
        :param targetUrl: スクレイピング対象サイトURL
        '''
        # スクレイピングに必要なオブジェクトを生成
        self.scraper = scrapelib.Scraper(requests_per_minute=100)
        self.page = self.scraper.get(self.url)
        self.soup = BeautifulSoup(self.page.content, "html.parser")
        # brタグを改行コードに置換
        for br in self.soup.find_all("br"):
            br.replace_with("\n")

    @abstractmethod
    def execute(self):
        '''
        スクレイピング処理を行う関数
        '''
        pass


class Scraping_BassOnTopACapella(ScrapingBase):
    def __init__(self):
        self.url = 'http://bassontop.tokyo.jp/a-cappella/yoyaku/takadanobaba/'
        super().__init__()

    def analyze_day_info(self, url):
        # 1日の空きスタジオの状況を取得
        table_page = self.scraper.get(self.url + url)
        table_soup = BeautifulSoup(table_page.content, "html.parser")

        # 部屋・時間毎の利用可否情報を取得
        availList = [tr.find_all('td') for tr in table_soup.find_all('tr')]
        timeList  = [th.getText() for th in table_soup.find_all('th')]
        roomList  = [cell.getText() for cell in availList[len(availList) - 1]
                         if re.match("^[0-9]{1,2}st", cell.getText())]

        def parseReservationInfo(availList_parse, row_idx) :
            '''
            取得した時間・部屋毎の予約状況を2次元配列にパースする。
            0        = 予約可能
            0以上の数 = 予約不可
            :param availList_parse: 変換後LIST
            :param row_idx: 処理中の行
            :return:　2次元配列化された時間・部屋毎の予約状況
            '''
            # セルの値が○の場合は0, ✗の場合は結合行の数のリストを作成
            if len(availList[row_idx]) == 0 :
                row = []
            else :
                row = [0 if cell.getText() == "○" else int(cell.get('rowspan') or 1) for cell in availList[row_idx]]

            # 前行に✗のセルが存在し、今の行にも存在する場合、✗データを今行の列に挿入
            if len(availList_parse) > 0 :
                pre_row = availList_parse[len(availList_parse) - 1]
                if len(row) > 0 :
                    for idx_l, pre_cell in enumerate(pre_row) :
                        if pre_cell > 1 :
                            row.insert(idx_l, pre_cell - 1)
                else :
                    row = [pre_cell - 1 for pre_cell in pre_row]

            # 今の行の情報を追加し、再帰判定
            availList_parse.append(row)
            if len(timeList)  == len(availList_parse) :
                return availList_parse
            else :
                return parseReservationInfo(availList_parse, row_idx + 1)

        # 時間毎のLISTから、部屋毎の使用可能状況のLISTに変換
        parsed_list =  parseReservationInfo(list(), 1)
        reserve_list_each_room = dict(zip(roomList, map(lambda avail : list(zip(avail, timeList)) ,zip(*parsed_list))))

    def execute(self):
        # サイドバーのカレンダーからアクセス出来る日付の一覧を取得
        calendar_url  = self.soup.find('frame', attrs={'name':'calendar'}).get('src')
        calendar_page = self.scraper.get(self.url + calendar_url)
        calendar_soup = BeautifulSoup(calendar_page.content, "html.parser")
        urlList = [td.find('a').get('href')for td in calendar_soup.find_all('td') if td.find('a') is not None]

        # サイドバーのカレンダーからアクセス出来る日程の情報にアクセス
        for idx, url in enumerate(urlList) :
            #解析対象日付文字列をURLから取得する
            date = re.search("[0-9]{4}\/[0-9]{1,2}\/[0-9]{1,2}", url).group()
            self.analyze_day_info(url)
            print(f"{idx + 1}/{len(urlList)}:{date} done")

if __name__ == '__main__':
    from timeit import Timer
    t = Timer(lambda: Scraping_BassOnTopACapella().execute())
    print(t.timeit(number=1))
