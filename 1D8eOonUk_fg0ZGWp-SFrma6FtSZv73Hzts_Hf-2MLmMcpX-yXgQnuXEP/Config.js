// Config.gs

const MODEL_NAME = "gemini-3.1-pro-preview";

const FACILITY_CONFIG = {
  1: { name: "愛媛県美術館", prompt: "愛媛県美術館の今後の展示スケジュールを取得し一覧するウェブページを作成してください。\nhttps://www.ehime-art.jp/\nhttps://www.ehime-art.jp/exhibition/rental.html\n貸しギャラリーでの展示も含めて下さい。" },
  2: { name: "萬翠荘", prompt: "晩翆荘の今後の展示スケジュールを取得し、一覧できるようなウェブページを作成してください。展示やコンサート、単日、短時間のイベントも全て含めて下さい。５月９日のイベントも含めて下さい。\nhttps://www.bansuisou.org/\nhttps://www.bansuisou.org/event/index.html" },
  3: { name: "坂の上の雲ミュージアム", prompt: "坂の上の雲ミュージアムの今後の展示スケジュールを取得し一覧するウェブページを作成してください。\nhttps://www.sakanouenokumomuseum.jp/event/event/\nhttps://www.sakanouenokumomuseum.jp/\nhttps://www.sakanouenokumomuseum.jp/display/" },
  4: { name: "松山市立子規記念博物館", prompt: "子規記念博物館の今後の展示スケジュールを取得し一覧するウェブページを作成してください。\nhttps://shiki-museum.com/\nhttps://shiki-museum.com/event/\nhttps://shiki-museum.com/information/" },
  5: { name: "道後公園 湯築城跡", prompt: "道後公園 湯築城跡 の今後の展示スケジュールを取得し一覧するウェブページを作成してください。\nhttps://dogokouen.jp/\nhttps://dogokouen.jp/event/\nhttps://dogokouen.jp/event/other/" },
  6: { name: "ミウラート・ヴィレッジ", prompt: "ミウラート・ヴィレッジ（三浦美術館）の今後の展示スケジュールを取得し一覧するウェブページを作成してください。\nhttps://www.miuraz.co.jp/miurart/\nhttps://www.miuraz.co.jp/miurart/main/\nhttps://www.miuraz.co.jp/miurart/info/" },
  7: { name: "セキ美術館", prompt: "セキ美術館の今後の展示スケジュールを取得し一覧するウェブページを作成してください。\nhttps://www.seki.co.jp/mus/\nhttps://www.seki.co.jp/mus/contents/exhibit" },
  8: { name: "秋山兄弟生誕地", prompt: "秋山兄弟生誕地の今後の展示スケジュールを取得し一覧するウェブページを作成してください。\nhttps://akiyama-kyodai.gr.jp/" },
  9: { name: "松山城 二之丸史跡庭園", prompt: "松山城 二之丸史跡庭園の今後の展示スケジュールを取得し一覧するウェブページを作成してください。\nhttps://www.matsuyamajo.jp/ninomaru/\nhttps://www.matsuyamajo.jp/event/\nhttps://www.matsuyamajo.jp/annualevents/\nhttps://www.matsuyamajo.jp/event/castle/\nhttps://www.matsuyamajo.jp/info/" },
  10: { name: "愛媛大学ミュージアム", prompt: "愛媛大学ミュージアムの今後の展示スケジュールを取得し一覧するウェブページを作成してください。\nhttps://www.ehime-u.ac.jp/about/ehime-u-museum/\nhttps://www.ehime-u.ac.jp/data_event/?start_date=&end_date=&s_cat%5B%5D=125&s_title=&s_type=all\nhttps://www.ehime-u.ac.jp/data_event/?s_cat[]=125\nhttps://www.facebook.com/EhimeUniversityMuseum/" }
};