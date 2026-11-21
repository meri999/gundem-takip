"""Panel görsel dili: lacivert/amber/gri palet, düz dolgu, gölgesiz, yalnızca yatay çizgiler.
Başlıklar Montserrat, kaynak notu ve gövde alt metni Times New Roman. Palet dışı renk kullanılmaz."""

BORDO = "#0B3C5D"
KIRMIZI = "#D9822B"
METIN = "#1D1D1B"
ZEMIN = "#E6EEF3"
ACIK_GRI = "#C5CED6"
GRI = "#4A5560"
SOLUK = "#3F7399"
SERI = [BORDO, KIRMIZI, GRI, SOLUK, ACIK_GRI]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Montserrat', Arial, sans-serif; color: {METIN}; }}
h1, h2, h3, h4 {{ font-family: 'Montserrat', Arial, sans-serif !important; color: {BORDO} !important; font-weight: 700 !important; }}
h1 {{ border-bottom: 3px solid {BORDO}; padding-bottom: .35rem; letter-spacing: -.01em; }}
h2, h3 {{ border-bottom: 1px solid {ACIK_GRI}; padding-bottom: .2rem; }}
a, a:visited {{ color: {BORDO}; }}
a:hover {{ color: {KIRMIZI}; }}
/* kaynak notu ve açıklamalar: Times New Roman, gri */
[data-testid="stCaptionContainer"], .kaynak {{ font-family: 'Times New Roman', Times, serif !important; color: {GRI} !important; font-size: .9rem; }}
/* sekmeler */
.stTabs [data-baseweb="tab-list"] {{ gap: 0; border-bottom: 1px solid {ACIK_GRI}; flex-wrap: wrap; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; color: {GRI}; padding: .55rem .9rem; }}
.stTabs [aria-selected="true"] {{ color: {BORDO} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {BORDO} !important; height: 3px; }}
/* düğme ve girdiler: düz dolgu, gölge yok */
.stButton>button, .stDownloadButton>button {{ background: {BORDO}; color: #fff; border: 0; border-radius: 2px; box-shadow: none; }}
.stButton>button:hover {{ background: {KIRMIZI}; color: #fff; }}
[data-baseweb="tag"] {{ background-color: {ZEMIN} !important; color: {BORDO} !important; border-radius: 2px; }}
[data-testid="stExpander"] {{ border: 1px solid {ACIK_GRI}; border-radius: 2px; box-shadow: none; }}
[data-testid="stAlert"] {{ background: {ZEMIN}; color: {METIN}; border-left: 4px solid {BORDO}; border-radius: 2px; }}
/* haber listesi */
.konu {{ display: inline-block; background: {ZEMIN}; color: {BORDO}; font-size: .72rem; padding: 0 .45rem;
        margin: .05rem .25rem 0 0; border-radius: 2px; font-weight: 600; }}
.hkaynak {{ color: {GRI}; font-family: 'Times New Roman', Times, serif; }}
/* yardım notu ve yayın fırsatı kartları */
.yardim {{ background: {ZEMIN}; border-left: 4px solid {BORDO}; padding: .5rem .8rem; margin: .2rem 0 .9rem;
          font-size: .88rem; color: {METIN}; }}
.firsat {{ border: 1px solid {ACIK_GRI}; border-top: 4px solid {BORDO}; padding: .6rem .8rem; margin-bottom: .7rem; }}
.firsat .fb {{ font-weight: 700; color: {BORDO}; font-size: 1rem; }}
.firsat .puan {{ float: right; background: {BORDO}; color: #fff; font-weight: 700; font-size: .8rem;
                padding: 0 .5rem; border-radius: 2px; }}
.firsat ul {{ margin: .35rem 0 0 1rem; padding: 0; font-size: .88rem; }}
.firsat .ozet {{ font-family: 'Times New Roman', Times, serif; color: {GRI}; font-size: .9rem; margin-top: .15rem; }}
.firsat .alt {{ font-weight: 700; font-size: .78rem; color: {GRI}; margin: .6rem 0 .1rem; letter-spacing: .02em; }}
.firsat .tez {{ font-size: .97rem; font-weight: 600; margin: .35rem 0 .2rem; }}
.firsat .hb {{ padding: .25rem 0; border-bottom: 1px solid {ACIK_GRI}; font-size: .92rem; }}
.firsat .hb:last-child {{ border-bottom: 0; }}
.guncel {{ font-family: 'Times New Roman', Times, serif; color: {GRI}; font-size: .9rem; margin: .45rem 0 .8rem; }}
/* ay takvimi */
.ay-baslik {{ background: {BORDO}; color: #fff; font-weight: 700; padding: .5rem .8rem; letter-spacing: .02em; margin-top: 1.2rem; }}
table.takvim {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
table.takvim th {{ background: {ZEMIN}; color: {BORDO}; font-size: .78rem; padding: .3rem; text-align: center; border-bottom: 2px solid {BORDO}; }}
table.takvim td {{ vertical-align: top; height: 110px; padding: .25rem .35rem; border-bottom: 1px solid {ACIK_GRI};
                  border-right: 0; font-size: .72rem; line-height: 1.25; }}
table.takvim td.bos {{ background: #fff; }}
table.takvim td.hs {{ background: #F5F8FA; }}
table.takvim td.bugun {{ outline: 2px solid {KIRMIZI}; outline-offset: -2px; }}
table.takvim td.gecmis {{ opacity: .55; }}
.gn {{ font-weight: 700; font-size: .85rem; color: {METIN}; }}
td.bugun .gn {{ color: {KIRMIZI}; }}
.ev {{ margin-top: .2rem; padding-left: .7rem; text-indent: -.7rem; color: {METIN}; }}
@media (max-width: 760px) {{ table.takvim td {{ height: 90px; font-size: .62rem; }} }}
</style>
"""


def plotly_tema(fig):
    """Plotly grafiğini panel diline çevirir."""
    fig.update_layout(
        font=dict(family="Montserrat, Arial, sans-serif", color=METIN),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", colorway=SERI,
        legend=dict(orientation="h", y=-0.2, title_text=""),
        margin=dict(t=30, l=10, r=10, b=10),
    )
    fig.update_xaxes(showgrid=False, linecolor=ACIK_GRI, tickfont=dict(color=GRI), title_font=dict(color=GRI))
    fig.update_yaxes(gridcolor=ACIK_GRI, gridwidth=0.5, zeroline=False, tickfont=dict(color=GRI),
                     title_font=dict(color=GRI))
    return fig
