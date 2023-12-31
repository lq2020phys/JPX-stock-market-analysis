import warnings, gc
import numpy as np
import pandas as pd
import matplotlib.colors
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import init_notebook_mode
from datetime import datetime, timedelta
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error
from lightgbm import LGBMRegressor
from decimal import ROUND_HALF_UP, Decimal

warnings.filterwarnings("ignore")
import plotly.figure_factory as ff

init_notebook_mode(connected=True)
temp = dict(layout=go.Layout(font=dict(family="Franklin Gothic", size=12), width=800))
colors = px.colors.qualitative.Plotly

train = pd.read_csv("../input/jpx-tokyo-stock-exchange-prediction/train_files/stock_prices.csv", parse_dates=['Date'])
stock_list = pd.read_csv("../input/jpx-tokyo-stock-exchange-prediction/stock_list.csv")

print("The training data begins on {} and ends on {}.\n".format(train.Date.min(), train.Date.max()))
display(train.describe().style.format('{:,.2f}'))

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:58:55.419637Z","iopub.execute_input":"2023-08-01T02:58:55.419971Z","iopub.status.idle":"2023-08-01T02:58:55.739276Z","shell.execute_reply.started":"2023-08-01T02:58:55.419941Z","shell.execute_reply":"2023-08-01T02:58:55.738307Z"}}
train_date = train.Date.unique()
returns = train.groupby('Date')['Target'].mean().mul(100).rename('Average Return')
close_avg = train.groupby('Date')['Close'].mean().rename('Closing Price')
vol_avg = train.groupby('Date')['Volume'].mean().rename('Volume')

fig = make_subplots(rows=3, cols=1,
                    shared_xaxes=True)
for i, j in enumerate([returns, close_avg, vol_avg]):
    fig.add_trace(go.Scatter(x=train_date, y=j, mode='lines',
                             name=j.name, marker_color=colors[i]), row=i + 1, col=1)
fig.update_xaxes(rangeslider_visible=False,
                 rangeselector=dict(
                     buttons=list([
                         dict(count=6, label="6m", step="month", stepmode="backward"),
                         dict(count=1, label="1y", step="year", stepmode="backward"),
                         dict(count=2, label="2y", step="year", stepmode="backward"),
                         dict(step="all")])),
                 row=1, col=1)
fig.update_layout(template=temp, title='JPX Market Average Stock Return, Closing Price, and Shares Traded',
                  hovermode='x unified', height=700,
                  yaxis1=dict(title='Stock Return', ticksuffix='%'),
                  yaxis2_title='Closing Price', yaxis3_title='Shares Traded',
                  showlegend=False)
fig.show()

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:58:55.741223Z","iopub.execute_input":"2023-08-01T02:58:55.741544Z","iopub.status.idle":"2023-08-01T02:58:58.000666Z","shell.execute_reply.started":"2023-08-01T02:58:55.741498Z","shell.execute_reply":"2023-08-01T02:58:57.999754Z"}}
stock_list['SectorName'] = [i.rstrip().lower().capitalize() for i in stock_list['17SectorName']]
stock_list['Name'] = [i.rstrip().lower().capitalize() for i in stock_list['Name']]
train_df = train.merge(stock_list[['SecuritiesCode', 'Name', 'SectorName']], on='SecuritiesCode', how='left')
train_df['Year'] = train_df['Date'].dt.year
display(train_df[train_df.Date > '2020-12-23'].head(n=50))
years = {year: pd.DataFrame() for year in train_df.Year.unique()[::-1]}
for key in years.keys():
    df = train_df[train_df.Year == key]
    years[key] = df.groupby('SectorName')['Target'].mean().mul(100).rename("Avg_return_{}".format(key))
df = pd.concat((years[i].to_frame() for i in years.keys()), axis=1)
df = df.sort_values(by="Avg_return_2021")
display(df.head(n=20))

fig = make_subplots(rows=1, cols=5, shared_yaxes=True)
for i, col in enumerate(df.columns):
    x = df[col]
    mask = x <= 0
    fig.add_trace(go.Bar(x=x[mask], y=df.index[mask], orientation='h',
                         text=x[mask], texttemplate='%{text:.2f}%', textposition='auto',
                         hovertemplate='Average Return in %{y} Stocks = %{x:.4f}%',
                         marker=dict(color='red', opacity=0.7), name=col[-4:]),
                  row=1, col=i + 1)
    fig.add_trace(go.Bar(x=x[~mask], y=df.index[~mask], orientation='h',
                         text=x[~mask], texttemplate='%{text:.2f}%', textposition='auto',
                         hovertemplate='Average Return in %{y} Stocks = %{x:.4f}%',
                         marker=dict(color='green', opacity=0.7), name=col[-4:]),
                  row=1, col=i + 1)
    fig.update_xaxes(range=(x.min() - .15, x.max() + .15), title='{} Returns'.format(col[-4:]),
                     showticklabels=False, row=1, col=i + 1)
fig.update_layout(template=temp, title='Yearly Average Stock Returns by Sector',
                  hovermode='closest', margin=dict(l=250, r=50),
                  height=600, width=1000, showlegend=False)
fig.show()

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:58:58.003135Z","iopub.execute_input":"2023-08-01T02:58:58.003479Z","iopub.status.idle":"2023-08-01T02:58:58.098814Z","shell.execute_reply.started":"2023-08-01T02:58:58.003443Z","shell.execute_reply":"2023-08-01T02:58:58.097961Z"}}
train_df = train_df[train_df.Date > '2020-12-23']
print("New Train Shape {}.\nMissing values in Target = {}".format(train_df.shape, train_df['Target'].isna().sum()))

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:58:58.100052Z","iopub.execute_input":"2023-08-01T02:58:58.100367Z","iopub.status.idle":"2023-08-01T02:58:58.987593Z","shell.execute_reply.started":"2023-08-01T02:58:58.100337Z","shell.execute_reply":"2023-08-01T02:58:58.986611Z"}}
fig = go.Figure()
x_hist = train_df['Target']
fig.add_trace(go.Histogram(x=x_hist * 100,
                           marker=dict(color=colors[0], opacity=0.7,
                                       line=dict(width=1, color=colors[0])),
                           xbins=dict(start=-40, end=40, size=1)))
fig.update_layout(template=temp, title='Target Distribution',
                  xaxis=dict(title='Stock Return', ticksuffix='%'), height=450)
fig.show()

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:58:58.988838Z","iopub.execute_input":"2023-08-01T02:58:58.989072Z","iopub.status.idle":"2023-08-01T02:59:01.304170Z","shell.execute_reply.started":"2023-08-01T02:58:58.989042Z","shell.execute_reply":"2023-08-01T02:59:01.303187Z"}}
pal = ['hsl(' + str(h) + ',50%' + ',50%)' for h in np.linspace(0, 360, 18)]  # hsl=(色相, 饱和度,亮度)
display(pal)
fig = go.Figure()
for i, sector in enumerate(df.index[::-1]):
    y_data = train_df[train_df['SectorName'] == sector]['Target']
    fig.add_trace(go.Box(y=y_data * 100, name=sector,
                         marker_color=pal[i], showlegend=False))
fig.update_layout(template=temp, title='Target Distribution by Sector',
                  yaxis=dict(title='Stock Return', ticksuffix='%'),
                  margin=dict(b=150), height=750, width=900)
fig.show()

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:59:01.305670Z","iopub.execute_input":"2023-08-01T02:59:01.305913Z","iopub.status.idle":"2023-08-01T02:59:07.176279Z","shell.execute_reply.started":"2023-08-01T02:59:01.305883Z","shell.execute_reply":"2023-08-01T02:59:07.175602Z"}}
# 计算每sector内股票平均的开盘，high，low等
train_date = train_df.Date.unique()
sectors = train_df.SectorName.unique().tolist()
sectors.insert(0, 'All')  # 插入列表insert(index,element)
open_avg = train_df.groupby('Date')['Open'].mean()
high_avg = train_df.groupby('Date')['High'].mean()
low_avg = train_df.groupby('Date')['Low'].mean()
close_avg = train_df.groupby('Date')['Close'].mean()
buttons = []

fig = go.Figure()
for i in range(18):
    if i != 0:
        open_avg = train_df[train_df.SectorName == sectors[i]].groupby('Date')['Open'].mean()
        high_avg = train_df[train_df.SectorName == sectors[i]].groupby('Date')['High'].mean()
        low_avg = train_df[train_df.SectorName == sectors[i]].groupby('Date')['Low'].mean()
        close_avg = train_df[train_df.SectorName == sectors[i]].groupby('Date')['Close'].mean()

    fig.add_trace(go.Candlestick(x=train_date, open=open_avg, high=high_avg,
                                 low=low_avg, close=close_avg, name=sectors[i],
                                 visible=(True if i == 0 else False)))

    visibility = [False] * len(sectors)
    visibility[i] = True
    button = dict(label=sectors[i],
                  method="update",
                  args=[{"visible": visibility}])
    buttons.append(button)

fig.update_xaxes(rangeslider_visible=True,
                 rangeselector=dict(
                     buttons=list([
                         dict(count=3, label="3m", step="month", stepmode="backward"),
                         dict(count=6, label="6m", step="month", stepmode="backward"),
                         dict(step="all")]), xanchor='left', yanchor='bottom', y=1.16, x=.01))
fig.update_layout(template=temp, title='Stock Price Movements by Sector',
                  hovermode='x unified', showlegend=False, width=1000,
                  updatemenus=[dict(active=0, type="dropdown",
                                    buttons=buttons, xanchor='left',
                                    yanchor='bottom', y=1.01, x=.01)],
                  yaxis=dict(title='Stock Price'))
fig.show()

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:59:07.177783Z","iopub.execute_input":"2023-08-01T02:59:07.178205Z","iopub.status.idle":"2023-08-01T02:59:08.959256Z","shell.execute_reply.started":"2023-08-01T02:59:07.178170Z","shell.execute_reply":"2023-08-01T02:59:08.958574Z"}}
stock = train_df.groupby('Name')['Target'].mean().mul(100)
stock_low = stock.nsmallest(7)[::-1].rename("Return")
stock_high = stock.nlargest(7).rename("Return")
stock = pd.concat([stock_high, stock_low], axis=0).reset_index()
# display(stock.head(n=50))
# 所有股票平均收益率最高的7个和最低的7个合并
stock['Sector'] = 'All'
for i in train_df.SectorName.unique():  # 计算每个sector内股票平均收益率最高的7个和最低的7个
    sector = train_df[train_df.SectorName == i].groupby('Name')['Target'].mean().mul(100)
    stock_low = sector.nsmallest(7)[::-1].rename("Return")
    stock_high = sector.nlargest(7).rename("Return")
    sector_stock = pd.concat([stock_high, stock_low], axis=0).reset_index()
    sector_stock['Sector'] = i
    stock = stock.append(sector_stock, ignore_index=True)

display(stock.head(n=30))
fig = go.Figure()
buttons = []
for i, sector in enumerate(stock.Sector.unique()):
    x = stock[stock.Sector == sector]['Name']
    y = stock[stock.Sector == sector]['Return']
    mask = y > 0
    fig.add_trace(go.Bar(x=x[mask], y=y[mask], text=y[mask],
                         texttemplate='%{text:.2f}%',
                         textposition='auto',
                         name=sector, visible=(False if i != 0 else True),
                         hovertemplate='%{x} average return: %{y:.3f}%',
                         marker=dict(color='green', opacity=0.7)))
    fig.add_trace(go.Bar(x=x[~mask], y=y[~mask], text=y[~mask],
                         texttemplate='%{text:.2f}%',
                         textposition='auto',
                         name=sector, visible=(False if i != 0 else True),
                         hovertemplate='%{x} average return: %{y:.3f}%',
                         marker=dict(color='red', opacity=0.7)))

    visibility = [False] * 2 * len(stock.Sector.unique())
    visibility[i * 2], visibility[i * 2 + 1] = True, True
    button = dict(label=sector,
                  method="update",
                  args=[{"visible": visibility}])
    buttons.append(button)

fig.update_layout(title='Stocks with Highest and Lowest Returns by Sector',
                  template=temp, yaxis=dict(title='Average Return', ticksuffix='%'),
                  updatemenus=[dict(active=0, type="dropdown",
                                    buttons=buttons, xanchor='left',
                                    yanchor='bottom', y=1.01, x=.01)],
                  margin=dict(b=150), showlegend=False, height=700, width=900)
fig.show()

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:59:08.960392Z","iopub.execute_input":"2023-08-01T02:59:08.961078Z","iopub.status.idle":"2023-08-01T02:59:09.959667Z","shell.execute_reply.started":"2023-08-01T02:59:08.961031Z","shell.execute_reply":"2023-08-01T02:59:09.958615Z"}}
# 每个交易日生成一个点，横轴纵轴分别为判断相关的股票
stocks = train_df[train_df.SecuritiesCode.isin([4169, 7089, 4582, 2158, 7036])]
df_pivot = stocks.pivot_table(index='Date', columns='Name', values='Close').reset_index()
display(df_pivot.head(n=20))
display(len(df_pivot))
pal = ['rgb' + str(i) for i in sns.color_palette("coolwarm", len(df_pivot))]

fig = ff.create_scatterplotmatrix(df_pivot.iloc[:, 1:], diag='histogram', name='')
fig.update_traces(marker=dict(color=pal, opacity=0.9, line_color='white', line_width=.5))
fig.update_layout(template=temp, title='Scatterplots of Highest Performing Stocks',
                  height=1000, width=1000, showlegend=False)
fig.show()

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:59:09.961129Z","iopub.execute_input":"2023-08-01T02:59:09.961420Z","iopub.status.idle":"2023-08-01T02:59:11.120589Z","shell.execute_reply.started":"2023-08-01T02:59:09.961383Z","shell.execute_reply":"2023-08-01T02:59:11.119572Z"}}
# 计算每只股票close和target的相关系数
corr = train_df.groupby('SecuritiesCode')[['Target', 'Close']].corr().unstack().iloc[:, 1]
stocks = corr.nlargest(10).rename("Return").reset_index()
display(stocks.head(n=20))
stocks = stocks.merge(train_df[['Name', 'SecuritiesCode']], on='SecuritiesCode').drop_duplicates()
display(stocks.head(n=20))
pal = sns.color_palette("magma_r", 14).as_hex()
rgb = ['rgba' + str(matplotlib.colors.to_rgba(i, 0.7)) for i in pal]

fig = go.Figure()
fig.add_trace(go.Bar(x=stocks.Name, y=stocks.Return, text=stocks.Return,
                     texttemplate='%{text:.2f}', name='', width=0.8,
                     textposition='outside', marker=dict(color=rgb, line=dict(color=pal, width=1)),
                     hovertemplate='Correlation of %{x} with target = %{y:.3f}'))
fig.update_layout(template=temp, title='Most Correlated Stocks with Target Variable',
                  yaxis=dict(title='Correlation', showticklabels=False),
                  xaxis=dict(title='Stock', tickangle=45), margin=dict(b=100),
                  width=800, height=500)
fig.show()

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:59:11.121835Z","iopub.execute_input":"2023-08-01T02:59:11.122104Z","iopub.status.idle":"2023-08-01T02:59:11.347401Z","shell.execute_reply.started":"2023-08-01T02:59:11.122072Z","shell.execute_reply":"2023-08-01T02:59:11.346403Z"}}
# pivot_table sector内对close取均值，再算sector间的相关系数
df_pivot = train_df.pivot_table(index='Date', columns='SectorName', values='Close', aggfunc='mean').reset_index()
# display(train_df[train_df.SectorName=='Foods'].head(n=50))
corr = df_pivot.corr().round(2)
mask = np.triu(np.ones_like(corr, dtype=bool))
c_mask = np.where(~mask, corr, 100)
c = []
for i in c_mask.tolist()[1:]:
    c.append([x for x in i if x != 100])

cor = c[::-1]
x = corr.index.tolist()[:-1]
y = corr.columns.tolist()[1:][::-1]
fig = ff.create_annotated_heatmap(z=cor, x=x, y=y,
                                  hovertemplate='Correlation between %{x} and %{y} stocks = %{z}',
                                  colorscale='viridis', name='')
fig.update_layout(template=temp, title='Stock Correlation between Sectors',
                  margin=dict(l=250, t=270), height=800, width=900,
                  yaxis=dict(showgrid=False, autorange='reversed'),
                  xaxis=dict(showgrid=False))
fig.show()


# %% [code] {"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:59:11.348781Z","iopub.execute_input":"2023-08-01T02:59:11.349054Z","iopub.status.idle":"2023-08-01T02:59:52.427322Z","shell.execute_reply.started":"2023-08-01T02:59:11.349020Z","shell.execute_reply":"2023-08-01T02:59:52.426362Z"}}
def adjust_price(price):
    """
    Args:
        price (pd.DataFrame)  : pd.DataFrame include stock_price
    Returns:
        price DataFrame (pd.DataFrame): stock_price with generated AdjustedClose
    """
    # transform Date column into datetime
    price.loc[:, "Date"] = pd.to_datetime(price.loc[:, "Date"], format="%Y-%m-%d")

    def generate_adjusted_close(df):
        """
        Args:
            df (pd.DataFrame)  : stock_price for a single SecuritiesCode
        Returns:
            df (pd.DataFrame): stock_price with AdjustedClose for a single SecuritiesCode
        """
        # sort data to generate CumulativeAdjustmentFactor
        df = df.sort_values("Date", ascending=False)
        # generate CumulativeAdjustmentFactor
        df.loc[:, "CumulativeAdjustmentFactor"] = df["AdjustmentFactor"].cumprod()
        # generate AdjustedClose
        df.loc[:, "AdjustedClose"] = (
                df["CumulativeAdjustmentFactor"] * df["Close"]
        ).map(lambda x: float(
            Decimal(str(x)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        ))
        # reverse order
        df = df.sort_values("Date")
        # to fill AdjustedClose, replace 0 into np.nan
        df.loc[df["AdjustedClose"] == 0, "AdjustedClose"] = np.nan
        # forward fill AdjustedClose
        df.loc[:, "AdjustedClose"] = df.loc[:, "AdjustedClose"].ffill()
        return df

    # generate AdjustedClose
    price = price.sort_values(["SecuritiesCode", "Date"])
    price = price.groupby("SecuritiesCode").apply(generate_adjusted_close).reset_index(drop=True)
    return price


train = train.drop('ExpectedDividend', axis=1).fillna(0)
prices = adjust_price(train)


# %% [code] {"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T02:59:52.430113Z","iopub.execute_input":"2023-08-01T02:59:52.430388Z","iopub.status.idle":"2023-08-01T03:00:07.159937Z","shell.execute_reply.started":"2023-08-01T02:59:52.430352Z","shell.execute_reply":"2023-08-01T03:00:07.159071Z"}}
def create_features(df):
    df = df.copy()
    col = 'AdjustedClose'
    periods = [5, 10, 20, 30, 50]
    for period in periods:
        df.loc[:, "Return_{}Day".format(period)] = df.groupby("SecuritiesCode")[col].pct_change(period)
        df.loc[:, "MovingAvg_{}Day".format(period)] = df.groupby("SecuritiesCode")[col].rolling(
            window=period).mean().values
        df.loc[:, "ExpMovingAvg_{}Day".format(period)] = df.groupby("SecuritiesCode")[col].ewm(span=period,
                                                                                               adjust=False).mean().values
        df.loc[:, "Volatility_{}Day".format(period)] = np.log(df[col]).groupby(df["SecuritiesCode"]).diff().rolling(
            period).std()
    return df


display(prices.head(n=20))
price_features = create_features(df=prices)
price_features.drop(['RowId', 'SupervisionFlag', 'AdjustmentFactor', 'CumulativeAdjustmentFactor', 'Close'], axis=1,
                    inplace=True)

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T03:00:07.161051Z","iopub.execute_input":"2023-08-01T03:00:07.161291Z","iopub.status.idle":"2023-08-01T03:00:15.261357Z","shell.execute_reply.started":"2023-08-01T03:00:07.161261Z","shell.execute_reply":"2023-08-01T03:00:15.260220Z"}}
# 画出每个sector均值的移动平均，指数移动平均等
display(price_features.head(n=60))
price_names = price_features.merge(stock_list[['SecuritiesCode', 'Name', 'SectorName']], on='SecuritiesCode').set_index(
    'Date')
price_names = price_names[price_names.index >= '2020-12-29']
price_names.fillna(0, inplace=True)
# display(price_names.head(n=20))
features = ['MovingAvg', 'ExpMovingAvg', 'Return', 'Volatility']
names = ['Average', 'Exp. Moving Average', 'Period', 'Volatility']
buttons = []

fig = make_subplots(rows=2, cols=2,
                    shared_xaxes=True,
                    vertical_spacing=0.1,
                    subplot_titles=('Adjusted Close Moving Average',
                                    'Exponential Moving Average',
                                    'Stock Return', 'Stock Volatility'))

for i, sector in enumerate(price_names.SectorName.unique()):

    sector_df = price_names[price_names.SectorName == sector]
    periods = [0, 10, 30, 50]
    colors = px.colors.qualitative.Vivid
    dash = ['solid', 'dash', 'longdash', 'dashdot', 'longdashdot']
    row, col = 1, 1

    for j, (feature, name) in enumerate(zip(features, names)):
        if j >= 2:
            row, periods = 2, [10, 30, 50]
            colors = px.colors.qualitative.Bold[1:]
        if j % 2 == 0:
            col = 1
        else:
            col = 2

        for k, period in enumerate(periods):
            if (k == 0) & (j < 2):
                plot_data = sector_df.groupby(sector_df.index)['AdjustedClose'].mean().rename('Adjusted Close')
            elif j >= 2:
                plot_data = sector_df.groupby(sector_df.index)['{}_{}Day'.format(feature, period)].mean().mul(
                    100).rename('{}-day {}'.format(period, name))
            else:
                plot_data = sector_df.groupby(sector_df.index)['{}_{}Day'.format(feature, period)].mean().rename(
                    '{}-day {}'.format(period, name))
            fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data, mode='lines',
                                     name=plot_data.name, marker_color=colors[k + 1],
                                     line=dict(width=2, dash=(dash[k] if j < 2 else 'solid')),
                                     showlegend=(True if (j == 0) or (j == 2) else False), legendgroup=row,
                                     visible=(False if i != 0 else True)), row=row, col=col)

    visibility = [False] * 14 * len(price_names.SectorName.unique())
    for l in range(i * 14, i * 14 + 14):
        visibility[l] = True
    button = dict(label=sector,
                  method="update",
                  args=[{"visible": visibility}])
    buttons.append(button)

fig.update_layout(title='Stock Price Moving Average, Return,<br>and Volatility by Sector',
                  template=temp, yaxis3_ticksuffix='%', yaxis4_ticksuffix='%',
                  legend_title_text='Period', legend_tracegroupgap=250,
                  updatemenus=[dict(active=0, type="dropdown",
                                    buttons=buttons, xanchor='left',
                                    yanchor='bottom', y=1.105, x=.01)],
                  hovermode='x unified', height=800, width=1200, margin=dict(t=150))
fig.show()


# %% [code] {"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T03:00:15.263099Z","iopub.execute_input":"2023-08-01T03:00:15.263362Z","iopub.status.idle":"2023-08-01T03:00:15.276450Z","shell.execute_reply.started":"2023-08-01T03:00:15.263330Z","shell.execute_reply":"2023-08-01T03:00:15.275359Z"}}
def calc_spread_return_sharpe(df: pd.DataFrame, portfolio_size: int = 200, toprank_weight_ratio: float = 2) -> float:
    """
    Args:
        df (pd.DataFrame): predicted results
        portfolio_size (int): # of equities to buy/sell
        toprank_weight_ratio (float): the relative weight of the most highly ranked stock compared to the least.
    Returns:
        (float): sharpe ratio
    """

    def _calc_spread_return_per_day(df, portfolio_size, toprank_weight_ratio):
        """
        Args:
            df (pd.DataFrame): predicted results
            portfolio_size (int): # of equities to buy/sell
            toprank_weight_ratio (float): the relative weight of the most highly ranked stock compared to the least.
        Returns:
            (float): spread return
        """
        assert df['Rank'].min() == 0
        assert df['Rank'].max() == len(df['Rank']) - 1
        weights = np.linspace(start=toprank_weight_ratio, stop=1, num=portfolio_size)
        purchase = (df.sort_values(by='Rank')['Target'][:portfolio_size] * weights).sum() / weights.mean()
        short = (df.sort_values(by='Rank', ascending=False)['Target'][:portfolio_size] * weights).sum() / weights.mean()
        return purchase - short

    buf = df.groupby('Date').apply(_calc_spread_return_per_day, portfolio_size, toprank_weight_ratio)
    sharpe_ratio = buf.mean() / buf.std()
    return sharpe_ratio


# %% [code] {"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T03:48:21.816068Z","iopub.execute_input":"2023-08-01T03:48:21.816405Z","iopub.status.idle":"2023-08-01T03:57:13.165339Z","shell.execute_reply.started":"2023-08-01T03:48:21.816365Z","shell.execute_reply":"2023-08-01T03:57:13.164259Z"}}
ts_fold = TimeSeriesSplit(n_splits=10, gap=10000)
# display(price_features.dropna().head(n=20))
prices = price_features.dropna().sort_values(['Date', 'SecuritiesCode'])
y = prices['Target'].to_numpy()
X = prices.drop(['Target'], axis=1)
# display(X.head(n=20))
# display(y)
feat_importance = pd.DataFrame()
sharpe_ratio = []

for fold, (train_idx, val_idx) in enumerate(ts_fold.split(X, y)):

    print("\n========================== Fold {} ==========================".format(fold + 1))
    X_train, y_train = X.iloc[train_idx, :], y[train_idx]
    X_valid, y_val = X.iloc[val_idx, :], y[val_idx]

    print("Train Date range: {} to {}".format(X_train.Date.min(), X_train.Date.max()))
    print("Valid Date range: {} to {}".format(X_valid.Date.min(), X_valid.Date.max()))

    X_train.drop(['Date', 'SecuritiesCode'], axis=1, inplace=True)
    # display(X_valid.head(n=20))
    X_val = X_valid[X_valid.columns[~X_valid.columns.isin(['Date', 'SecuritiesCode'])]]  # 时间序列的交叉验证，验证集一定发生在训练集后面。
    val_dates = X_valid.Date.unique()[1:-1]  # 验证集应在每一天包含完整的所有股票，split时可能导致不完整，所以去掉验证集中最早和最晚的一天
    # display(X_val.head(n=20))
    # display(val_dates)
    print("\nTrain Shape: {} {}, Valid Shape: {} {}".format(X_train.shape, y_train.shape, X_val.shape, y_val.shape))

    params = {'n_estimators': 500,
              'num_leaves': 100,
              'learning_rate': 0.1,
              'colsample_bytree': 0.9,
              'subsample': 0.8,
              'reg_alpha': 0.4,
              'metric': 'mae',
              'random_state': 21}

    gbm = LGBMRegressor(**params).fit(X_train, y_train,
                                      eval_set=[(X_train, y_train), (X_val, y_val)],
                                      verbose=300,
                                      eval_metric=['mae', 'mse'])
    y_pred = gbm.predict(X_val)
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    mae = mean_absolute_error(y_val, y_pred)
    feat_importance["Importance_Fold" + str(fold)] = gbm.feature_importances_
    feat_importance.set_index(X_train.columns, inplace=True)

    rank = []
    X_val_df = X_valid[X_valid.Date.isin(val_dates)]
    # display(X_val_df.head(n=20))
    for i in X_val_df.Date.unique():  # 在验证集每一天按《预测值》排序rank
        temp_df = X_val_df[X_val_df.Date == i].drop(['Date', 'SecuritiesCode'], axis=1)
        temp_df["pred"] = gbm.predict(temp_df)
        temp_df["Rank"] = (temp_df["pred"].rank(method="first", ascending=False) - 1).astype(int)
        rank.append(temp_df["Rank"].values)

    stock_rank = pd.Series([x for y in rank for x in y], name="Rank")
    df = pd.concat([X_val_df.reset_index(drop=True), stock_rank,
                    prices[prices.Date.isin(val_dates)]['Target'].reset_index(drop=True)], axis=1)
    # display(df.head(n=20))
    sharpe = calc_spread_return_sharpe(df)
    sharpe_ratio.append(sharpe)
    print("Valid Sharpe: {}, RMSE: {}, MAE: {}".format(sharpe, rmse, mae))

    del X_train, y_train, X_val, y_val
    gc.collect()

print("\nAverage cross-validation Sharpe Ratio: {:.4f}, standard deviation = {:.2f}.".format(np.mean(sharpe_ratio),
                                                                                             np.std(sharpe_ratio)))

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T03:57:17.942686Z","iopub.execute_input":"2023-08-01T03:57:17.943029Z","iopub.status.idle":"2023-08-01T03:57:18.162274Z","shell.execute_reply.started":"2023-08-01T03:57:17.942991Z","shell.execute_reply":"2023-08-01T03:57:18.161458Z"}}
feat_importance['avg'] = feat_importance.mean(axis=1)
feat_importance = feat_importance.sort_values(by='avg', ascending=True)
pal = sns.color_palette("plasma_r", 29).as_hex()[2:]

fig = go.Figure()
for i in range(len(feat_importance.index)):
    fig.add_shape(dict(type="line", y0=i, y1=i, x0=0, x1=feat_importance['avg'][i],
                       line_color=pal[::-1][i], opacity=0.7, line_width=4))
fig.add_trace(go.Scatter(x=feat_importance['avg'], y=feat_importance.index, mode='markers',
                         marker_color=pal[::-1], marker_size=8,
                         hovertemplate='%{y} Importance = %{x:.0f}<extra></extra>'))
fig.update_layout(template=temp, title='Overall Feature Importance',
                  xaxis=dict(title='Average Importance', zeroline=False),
                  yaxis_showgrid=False, margin=dict(l=120, t=80),
                  height=700, width=800)
fig.show()

# %% [code] {"_kg_hide-input":true,"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T03:57:59.051361Z","iopub.execute_input":"2023-08-01T03:57:59.051669Z","iopub.status.idle":"2023-08-01T03:58:51.745242Z","shell.execute_reply.started":"2023-08-01T03:57:59.051634Z","shell.execute_reply":"2023-08-01T03:58:51.744545Z"}}
cols_fin = feat_importance.avg.nlargest(11).index.tolist()
cols_fin.extend(('Open', 'High', 'Low'))
display(prices.head(n=20))
X_train = prices[cols_fin]
y_train = prices['Target']
gbm = LGBMRegressor(**params).fit(X_train, y_train)

# %% [code] {"jupyter":{"outputs_hidden":false},"execution":{"iopub.status.busy":"2023-08-01T03:59:04.996704Z","iopub.execute_input":"2023-08-01T03:59:04.997037Z","iopub.status.idle":"2023-08-01T03:59:35.506736Z","shell.execute_reply.started":"2023-08-01T03:59:04.997001Z","shell.execute_reply":"2023-08-01T03:59:35.505938Z"}}
import jpx_tokyo_market_prediction

jpx_tokyo_market_prediction.make_env.__called__ = False
env = jpx_tokyo_market_prediction.make_env()
iter_test = env.iter_test()

# display(train.head(n=20))

cols = ['Date', 'SecuritiesCode', 'Open', 'High', 'Low', 'Close', 'Volume', 'AdjustmentFactor']
train = train[train.Date >= '2021-08-01'][cols]

counter = 0
for (prices, options, financials, trades, secondary_prices, sample_prediction) in iter_test:

    current_date = prices["Date"].iloc[0]
    display(current_date)
    if counter == 0:
        df_price_raw = train.loc[train["Date"] < current_date]
    df_price_raw = pd.concat([df_price_raw, prices[cols]]).reset_index(drop=True)
    df_price = adjust_price(df_price_raw)
    features = create_features(df=df_price)
    display(features.head(n=90))
    feat = features[features.Date == current_date][cols_fin]
    feat["pred"] = gbm.predict(feat)
    feat["Rank"] = (feat["pred"].rank(method="first", ascending=False) - 1).astype(int)
    sample_prediction["Rank"] = feat["Rank"].values
    display(sample_prediction.head())

    assert sample_prediction["Rank"].notna().all()
    assert sample_prediction["Rank"].min() == 0
    assert sample_prediction["Rank"].max() == len(sample_prediction["Rank"]) - 1

    env.predict(sample_prediction)
    counter += 1