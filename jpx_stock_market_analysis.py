{"metadata":{"kernelspec":{"language":"python","display_name":"Python 3","name":"python3"},"language_info":{"pygments_lexer":"ipython3","nbconvert_exporter":"python","version":"3.6.4","file_extension":".py","codemirror_mode":{"name":"ipython","version":3},"name":"python","mimetype":"text/x-python"}},"nbformat_minor":4,"nbformat":4,"cells":[{"cell_type":"code","source":"# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:58:46.730031Z\",\"iopub.execute_input\":\"2023-08-01T02:58:46.730605Z\",\"iopub.status.idle\":\"2023-08-01T02:58:55.415747Z\",\"shell.execute_reply.started\":\"2023-08-01T02:58:46.730511Z\",\"shell.execute_reply\":\"2023-08-01T02:58:55.415111Z\"}}\nimport warnings, gc\nimport numpy as np \nimport pandas as pd\nimport matplotlib.colors\nimport seaborn as sns\nimport plotly.express as px\nimport plotly.graph_objects as go\nfrom plotly.subplots import make_subplots\nfrom plotly.offline import init_notebook_mode\nfrom datetime import datetime, timedelta\nfrom sklearn.model_selection import TimeSeriesSplit\nfrom sklearn.metrics import mean_squared_error,mean_absolute_error\nfrom lightgbm import LGBMRegressor\nfrom decimal import ROUND_HALF_UP, Decimal\nwarnings.filterwarnings(\"ignore\")\nimport plotly.figure_factory as ff\n\ninit_notebook_mode(connected=True)\ntemp = dict(layout=go.Layout(font=dict(family=\"Franklin Gothic\", size=12), width=800))\ncolors=px.colors.qualitative.Plotly\n\ntrain=pd.read_csv(\"../input/jpx-tokyo-stock-exchange-prediction/train_files/stock_prices.csv\", parse_dates=['Date'])\nstock_list=pd.read_csv(\"../input/jpx-tokyo-stock-exchange-prediction/stock_list.csv\")\n\nprint(\"The training data begins on {} and ends on {}.\\n\".format(train.Date.min(),train.Date.max()))\ndisplay(train.describe().style.format('{:,.2f}'))\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:58:55.419637Z\",\"iopub.execute_input\":\"2023-08-01T02:58:55.419971Z\",\"iopub.status.idle\":\"2023-08-01T02:58:55.739276Z\",\"shell.execute_reply.started\":\"2023-08-01T02:58:55.419941Z\",\"shell.execute_reply\":\"2023-08-01T02:58:55.738307Z\"}}\ntrain_date=train.Date.unique()\nreturns=train.groupby('Date')['Target'].mean().mul(100).rename('Average Return')\nclose_avg=train.groupby('Date')['Close'].mean().rename('Closing Price')\nvol_avg=train.groupby('Date')['Volume'].mean().rename('Volume')\n\nfig = make_subplots(rows=3, cols=1, \n                    shared_xaxes=True)\nfor i, j in enumerate([returns, close_avg, vol_avg]):\n    fig.add_trace(go.Scatter(x=train_date, y=j, mode='lines',\n                             name=j.name, marker_color=colors[i]), row=i+1, col=1)\nfig.update_xaxes(rangeslider_visible=False,\n                 rangeselector=dict(\n                     buttons=list([\n                         dict(count=6, label=\"6m\", step=\"month\", stepmode=\"backward\"),\n                         dict(count=1, label=\"1y\", step=\"year\", stepmode=\"backward\"),\n                         dict(count=2, label=\"2y\", step=\"year\", stepmode=\"backward\"),\n                         dict(step=\"all\")])),\n                 row=1,col=1)\nfig.update_layout(template=temp,title='JPX Market Average Stock Return, Closing Price, and Shares Traded', \n                  hovermode='x unified', height=700, \n                  yaxis1=dict(title='Stock Return', ticksuffix='%'), \n                  yaxis2_title='Closing Price', yaxis3_title='Shares Traded',\n                  showlegend=False)\nfig.show()\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:58:55.741223Z\",\"iopub.execute_input\":\"2023-08-01T02:58:55.741544Z\",\"iopub.status.idle\":\"2023-08-01T02:58:58.000666Z\",\"shell.execute_reply.started\":\"2023-08-01T02:58:55.741498Z\",\"shell.execute_reply\":\"2023-08-01T02:58:57.999754Z\"}}\nstock_list['SectorName']=[i.rstrip().lower().capitalize() for i in stock_list['17SectorName']]\nstock_list['Name']=[i.rstrip().lower().capitalize() for i in stock_list['Name']]\ntrain_df = train.merge(stock_list[['SecuritiesCode','Name','SectorName']], on='SecuritiesCode', how='left')\ntrain_df['Year'] = train_df['Date'].dt.year\ndisplay(train_df[train_df.Date>'2020-12-23'].head(n=50))\nyears = {year: pd.DataFrame() for year in train_df.Year.unique()[::-1]}\nfor key in years.keys():\n    df=train_df[train_df.Year == key]\n    years[key] = df.groupby('SectorName')['Target'].mean().mul(100).rename(\"Avg_return_{}\".format(key))\ndf=pd.concat((years[i].to_frame() for i in years.keys()), axis=1)\ndf=df.sort_values(by=\"Avg_return_2021\")\ndisplay(df.head(n=20))\n\nfig = make_subplots(rows=1, cols=5, shared_yaxes=True)\nfor i, col in enumerate(df.columns):\n    x = df[col]\n    mask = x<=0\n    fig.add_trace(go.Bar(x=x[mask], y=df.index[mask],orientation='h', \n                         text=x[mask], texttemplate='%{text:.2f}%',textposition='auto',\n                         hovertemplate='Average Return in %{y} Stocks = %{x:.4f}%',\n                         marker=dict(color='red', opacity=0.7),name=col[-4:]), \n                  row=1, col=i+1)\n    fig.add_trace(go.Bar(x=x[~mask], y=df.index[~mask],orientation='h', \n                         text=x[~mask], texttemplate='%{text:.2f}%', textposition='auto', \n                         hovertemplate='Average Return in %{y} Stocks = %{x:.4f}%',\n                         marker=dict(color='green', opacity=0.7),name=col[-4:]), \n                  row=1, col=i+1)\n    fig.update_xaxes(range=(x.min()-.15,x.max()+.15), title='{} Returns'.format(col[-4:]), \n                     showticklabels=False, row=1, col=i+1)\nfig.update_layout(template=temp,title='Yearly Average Stock Returns by Sector', \n                  hovermode='closest',margin=dict(l=250,r=50),\n                  height=600, width=1000, showlegend=False)\nfig.show()\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:58:58.003135Z\",\"iopub.execute_input\":\"2023-08-01T02:58:58.003479Z\",\"iopub.status.idle\":\"2023-08-01T02:58:58.098814Z\",\"shell.execute_reply.started\":\"2023-08-01T02:58:58.003443Z\",\"shell.execute_reply\":\"2023-08-01T02:58:58.097961Z\"}}\ntrain_df=train_df[train_df.Date>'2020-12-23']\nprint(\"New Train Shape {}.\\nMissing values in Target = {}\".format(train_df.shape,train_df['Target'].isna().sum()))\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:58:58.100052Z\",\"iopub.execute_input\":\"2023-08-01T02:58:58.100367Z\",\"iopub.status.idle\":\"2023-08-01T02:58:58.987593Z\",\"shell.execute_reply.started\":\"2023-08-01T02:58:58.100337Z\",\"shell.execute_reply\":\"2023-08-01T02:58:58.986611Z\"}}\nfig = go.Figure()\nx_hist=train_df['Target']\nfig.add_trace(go.Histogram(x=x_hist*100,\n                           marker=dict(color=colors[0], opacity=0.7, \n                                       line=dict(width=1, color=colors[0])),\n                           xbins=dict(start=-40,end=40,size=1)))\nfig.update_layout(template=temp,title='Target Distribution', \n                  xaxis=dict(title='Stock Return',ticksuffix='%'), height=450)\nfig.show()\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:58:58.988838Z\",\"iopub.execute_input\":\"2023-08-01T02:58:58.989072Z\",\"iopub.status.idle\":\"2023-08-01T02:59:01.304170Z\",\"shell.execute_reply.started\":\"2023-08-01T02:58:58.989042Z\",\"shell.execute_reply\":\"2023-08-01T02:59:01.303187Z\"}}\npal = ['hsl('+str(h)+',50%'+',50%)' for h in np.linspace(0, 360, 18)]# hsl=(色相, 饱和度,亮度)\ndisplay(pal)\nfig = go.Figure()\nfor i, sector in enumerate(df.index[::-1]):\n    y_data=train_df[train_df['SectorName']==sector]['Target']\n    fig.add_trace(go.Box(y=y_data*100, name=sector,\n                         marker_color=pal[i], showlegend=False))\nfig.update_layout(template=temp, title='Target Distribution by Sector',\n                  yaxis=dict(title='Stock Return',ticksuffix='%'),\n                  margin=dict(b=150), height=750, width=900)\nfig.show()\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:59:01.305670Z\",\"iopub.execute_input\":\"2023-08-01T02:59:01.305913Z\",\"iopub.status.idle\":\"2023-08-01T02:59:07.176279Z\",\"shell.execute_reply.started\":\"2023-08-01T02:59:01.305883Z\",\"shell.execute_reply\":\"2023-08-01T02:59:07.175602Z\"}}\n#计算每sector内股票平均的开盘，high，low等\ntrain_date=train_df.Date.unique()\nsectors=train_df.SectorName.unique().tolist()\nsectors.insert(0, 'All') #插入列表insert(index,element)\nopen_avg=train_df.groupby('Date')['Open'].mean()\nhigh_avg=train_df.groupby('Date')['High'].mean()\nlow_avg=train_df.groupby('Date')['Low'].mean()\nclose_avg=train_df.groupby('Date')['Close'].mean() \nbuttons=[]\n\nfig = go.Figure()\nfor i in range(18):\n    if i != 0:\n        open_avg=train_df[train_df.SectorName==sectors[i]].groupby('Date')['Open'].mean()\n        high_avg=train_df[train_df.SectorName==sectors[i]].groupby('Date')['High'].mean()\n        low_avg=train_df[train_df.SectorName==sectors[i]].groupby('Date')['Low'].mean()\n        close_avg=train_df[train_df.SectorName==sectors[i]].groupby('Date')['Close'].mean()        \n    \n    fig.add_trace(go.Candlestick(x=train_date, open=open_avg, high=high_avg,\n                                 low=low_avg, close=close_avg, name=sectors[i],\n                                 visible=(True if i==0 else False)))\n    \n    visibility=[False]*len(sectors)\n    visibility[i]=True\n    button = dict(label = sectors[i],\n                  method = \"update\",\n                  args=[{\"visible\": visibility}])\n    buttons.append(button)\n    \nfig.update_xaxes(rangeslider_visible=True,\n                 rangeselector=dict(\n                     buttons=list([\n                         dict(count=3, label=\"3m\", step=\"month\", stepmode=\"backward\"),\n                         dict(count=6, label=\"6m\", step=\"month\", stepmode=\"backward\"),\n                         dict(step=\"all\")]), xanchor='left',yanchor='bottom', y=1.16, x=.01))\nfig.update_layout(template=temp,title='Stock Price Movements by Sector', \n                  hovermode='x unified', showlegend=False, width=1000,\n                  updatemenus=[dict(active=0, type=\"dropdown\",\n                                    buttons=buttons, xanchor='left',\n                                    yanchor='bottom', y=1.01, x=.01)],\n                  yaxis=dict(title='Stock Price'))\nfig.show()\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:59:07.177783Z\",\"iopub.execute_input\":\"2023-08-01T02:59:07.178205Z\",\"iopub.status.idle\":\"2023-08-01T02:59:08.959256Z\",\"shell.execute_reply.started\":\"2023-08-01T02:59:07.178170Z\",\"shell.execute_reply\":\"2023-08-01T02:59:08.958574Z\"}}\nstock=train_df.groupby('Name')['Target'].mean().mul(100)\nstock_low=stock.nsmallest(7)[::-1].rename(\"Return\")\nstock_high=stock.nlargest(7).rename(\"Return\")\nstock=pd.concat([stock_high, stock_low], axis=0).reset_index()\n#display(stock.head(n=50))\n#所有股票平均收益率最高的7个和最低的7个合并\nstock['Sector']='All'\nfor i in train_df.SectorName.unique():  #计算每个sector内股票平均收益率最高的7个和最低的7个\n    sector=train_df[train_df.SectorName==i].groupby('Name')['Target'].mean().mul(100)\n    stock_low=sector.nsmallest(7)[::-1].rename(\"Return\")\n    stock_high=sector.nlargest(7).rename(\"Return\")\n    sector_stock=pd.concat([stock_high, stock_low], axis=0).reset_index()\n    sector_stock['Sector']=i\n    stock=stock.append(sector_stock,ignore_index=True)\n\ndisplay(stock.head(n=30))\nfig=go.Figure()\nbuttons = []\nfor i, sector in enumerate(stock.Sector.unique()):\n    \n    x=stock[stock.Sector==sector]['Name']\n    y=stock[stock.Sector==sector]['Return']\n    mask=y>0\n    fig.add_trace(go.Bar(x=x[mask], y=y[mask], text=y[mask], \n                         texttemplate='%{text:.2f}%',\n                         textposition='auto',\n                         name=sector, visible=(False if i != 0 else True),\n                         hovertemplate='%{x} average return: %{y:.3f}%',\n                         marker=dict(color='green', opacity=0.7)))\n    fig.add_trace(go.Bar(x=x[~mask], y=y[~mask], text=y[~mask], \n                         texttemplate='%{text:.2f}%',\n                         textposition='auto',\n                         name=sector, visible=(False if i != 0 else True),\n                         hovertemplate='%{x} average return: %{y:.3f}%',\n                         marker=dict(color='red', opacity=0.7)))\n    \n    visibility=[False]*2*len(stock.Sector.unique())\n    visibility[i*2],visibility[i*2+1]=True,True\n    button = dict(label = sector,\n                  method = \"update\",\n                  args=[{\"visible\": visibility}])\n    buttons.append(button)\n\nfig.update_layout(title='Stocks with Highest and Lowest Returns by Sector',\n                  template=temp, yaxis=dict(title='Average Return', ticksuffix='%'),\n                  updatemenus=[dict(active=0, type=\"dropdown\",\n                                    buttons=buttons, xanchor='left',\n                                    yanchor='bottom', y=1.01, x=.01)], \n                  margin=dict(b=150),showlegend=False,height=700, width=900)\nfig.show()\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:59:08.960392Z\",\"iopub.execute_input\":\"2023-08-01T02:59:08.961078Z\",\"iopub.status.idle\":\"2023-08-01T02:59:09.959667Z\",\"shell.execute_reply.started\":\"2023-08-01T02:59:08.961031Z\",\"shell.execute_reply\":\"2023-08-01T02:59:09.958615Z\"}}\n#每个交易日生成一个点，横轴纵轴分别为判断相关的股票\nstocks=train_df[train_df.SecuritiesCode.isin([4169,7089,4582,2158,7036])]\ndf_pivot=stocks.pivot_table(index='Date', columns='Name', values='Close').reset_index()\ndisplay(df_pivot.head(n=20))\ndisplay(len(df_pivot))\npal=['rgb'+str(i) for i in sns.color_palette(\"coolwarm\", len(df_pivot))]\n\nfig = ff.create_scatterplotmatrix(df_pivot.iloc[:,1:], diag='histogram', name='')\nfig.update_traces(marker=dict(color=pal, opacity=0.9, line_color='white', line_width=.5))\nfig.update_layout(template=temp, title='Scatterplots of Highest Performing Stocks', \n                  height=1000, width=1000, showlegend=False)\nfig.show()\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:59:09.961129Z\",\"iopub.execute_input\":\"2023-08-01T02:59:09.961420Z\",\"iopub.status.idle\":\"2023-08-01T02:59:11.120589Z\",\"shell.execute_reply.started\":\"2023-08-01T02:59:09.961383Z\",\"shell.execute_reply\":\"2023-08-01T02:59:11.119572Z\"}}\n#计算每只股票close和target的相关系数\ncorr=train_df.groupby('SecuritiesCode')[['Target','Close']].corr().unstack().iloc[:,1]\nstocks=corr.nlargest(10).rename(\"Return\").reset_index()\ndisplay(stocks.head(n=20))\nstocks=stocks.merge(train_df[['Name','SecuritiesCode']], on='SecuritiesCode').drop_duplicates()\ndisplay(stocks.head(n=20))\npal=sns.color_palette(\"magma_r\", 14).as_hex()\nrgb=['rgba'+str(matplotlib.colors.to_rgba(i,0.7)) for i in pal]\n\nfig = go.Figure()\nfig.add_trace(go.Bar(x=stocks.Name, y=stocks.Return, text=stocks.Return, \n                     texttemplate='%{text:.2f}', name='', width=0.8,\n                     textposition='outside',marker=dict(color=rgb, line=dict(color=pal,width=1)),\n                     hovertemplate='Correlation of %{x} with target = %{y:.3f}'))\nfig.update_layout(template=temp, title='Most Correlated Stocks with Target Variable',\n                  yaxis=dict(title='Correlation',showticklabels=False), \n                  xaxis=dict(title='Stock',tickangle=45), margin=dict(b=100),\n                  width=800,height=500)\nfig.show()\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:59:11.121835Z\",\"iopub.execute_input\":\"2023-08-01T02:59:11.122104Z\",\"iopub.status.idle\":\"2023-08-01T02:59:11.347401Z\",\"shell.execute_reply.started\":\"2023-08-01T02:59:11.122072Z\",\"shell.execute_reply\":\"2023-08-01T02:59:11.346403Z\"}}\n#pivot_table sector内对close取均值，再算sector间的相关系数\ndf_pivot=train_df.pivot_table(index='Date', columns='SectorName', values='Close',aggfunc='mean').reset_index()\n#display(train_df[train_df.SectorName=='Foods'].head(n=50))\ncorr=df_pivot.corr().round(2)\nmask=np.triu(np.ones_like(corr, dtype=bool))\nc_mask = np.where(~mask, corr, 100)\nc=[]\nfor i in c_mask.tolist()[1:]:\n    c.append([x for x in i if x != 100])\n    \ncor=c[::-1]\nx=corr.index.tolist()[:-1]\ny=corr.columns.tolist()[1:][::-1]\nfig=ff.create_annotated_heatmap(z=cor, x=x, y=y, \n                                hovertemplate='Correlation between %{x} and %{y} stocks = %{z}',\n                                colorscale='viridis', name='')\nfig.update_layout(template=temp, title='Stock Correlation between Sectors',\n                  margin=dict(l=250,t=270),height=800,width=900,\n                  yaxis=dict(showgrid=False, autorange='reversed'),\n                  xaxis=dict(showgrid=False))\nfig.show()\n\n# %% [code] {\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:59:11.348781Z\",\"iopub.execute_input\":\"2023-08-01T02:59:11.349054Z\",\"iopub.status.idle\":\"2023-08-01T02:59:52.427322Z\",\"shell.execute_reply.started\":\"2023-08-01T02:59:11.349020Z\",\"shell.execute_reply\":\"2023-08-01T02:59:52.426362Z\"}}\ndef adjust_price(price):\n    \"\"\"\n    Args:\n        price (pd.DataFrame)  : pd.DataFrame include stock_price\n    Returns:\n        price DataFrame (pd.DataFrame): stock_price with generated AdjustedClose\n    \"\"\"\n    # transform Date column into datetime\n    price.loc[: ,\"Date\"] = pd.to_datetime(price.loc[: ,\"Date\"], format=\"%Y-%m-%d\")\n\n    def generate_adjusted_close(df):\n        \"\"\"\n        Args:\n            df (pd.DataFrame)  : stock_price for a single SecuritiesCode\n        Returns:\n            df (pd.DataFrame): stock_price with AdjustedClose for a single SecuritiesCode\n        \"\"\"\n        # sort data to generate CumulativeAdjustmentFactor\n        df = df.sort_values(\"Date\", ascending=False)\n        # generate CumulativeAdjustmentFactor\n        df.loc[:, \"CumulativeAdjustmentFactor\"] = df[\"AdjustmentFactor\"].cumprod()\n        # generate AdjustedClose\n        df.loc[:, \"AdjustedClose\"] = (\n            df[\"CumulativeAdjustmentFactor\"] * df[\"Close\"]\n        ).map(lambda x: float(\n            Decimal(str(x)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)\n        ))\n        # reverse order\n        df = df.sort_values(\"Date\")\n        # to fill AdjustedClose, replace 0 into np.nan\n        df.loc[df[\"AdjustedClose\"] == 0, \"AdjustedClose\"] = np.nan\n        # forward fill AdjustedClose\n        df.loc[:, \"AdjustedClose\"] = df.loc[:, \"AdjustedClose\"].ffill()\n        return df\n    \n    # generate AdjustedClose\n    price = price.sort_values([\"SecuritiesCode\", \"Date\"])\n    price = price.groupby(\"SecuritiesCode\").apply(generate_adjusted_close).reset_index(drop=True)\n    return price\n\ntrain=train.drop('ExpectedDividend',axis=1).fillna(0)\nprices=adjust_price(train)\n\n# %% [code] {\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T02:59:52.430113Z\",\"iopub.execute_input\":\"2023-08-01T02:59:52.430388Z\",\"iopub.status.idle\":\"2023-08-01T03:00:07.159937Z\",\"shell.execute_reply.started\":\"2023-08-01T02:59:52.430352Z\",\"shell.execute_reply\":\"2023-08-01T03:00:07.159071Z\"}}\ndef create_features(df):\n    df=df.copy()\n    col='AdjustedClose'\n    periods=[5,10,20,30,50]\n    for period in periods:\n        df.loc[:,\"Return_{}Day\".format(period)] = df.groupby(\"SecuritiesCode\")[col].pct_change(period)\n        df.loc[:,\"MovingAvg_{}Day\".format(period)] = df.groupby(\"SecuritiesCode\")[col].rolling(window=period).mean().values\n        df.loc[:,\"ExpMovingAvg_{}Day\".format(period)] = df.groupby(\"SecuritiesCode\")[col].ewm(span=period,adjust=False).mean().values\n        df.loc[:,\"Volatility_{}Day\".format(period)] = np.log(df[col]).groupby(df[\"SecuritiesCode\"]).diff().rolling(period).std()\n    return df\ndisplay(prices.head(n=20))\nprice_features=create_features(df=prices)\nprice_features.drop(['RowId','SupervisionFlag','AdjustmentFactor','CumulativeAdjustmentFactor','Close'],axis=1,inplace=True)\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T03:00:07.161051Z\",\"iopub.execute_input\":\"2023-08-01T03:00:07.161291Z\",\"iopub.status.idle\":\"2023-08-01T03:00:15.261357Z\",\"shell.execute_reply.started\":\"2023-08-01T03:00:07.161261Z\",\"shell.execute_reply\":\"2023-08-01T03:00:15.260220Z\"}}\n#画出每个sector均值的移动平均，指数移动平均等\ndisplay(price_features.head(n=60))\nprice_names=price_features.merge(stock_list[['SecuritiesCode','Name','SectorName']], on='SecuritiesCode').set_index('Date')\nprice_names=price_names[price_names.index>='2020-12-29']\nprice_names.fillna(0, inplace=True)\n#display(price_names.head(n=20))\nfeatures=['MovingAvg','ExpMovingAvg','Return', 'Volatility']\nnames=['Average', 'Exp. Moving Average', 'Period', 'Volatility']\nbuttons=[]\n\nfig = make_subplots(rows=2, cols=2, \n                    shared_xaxes=True, \n                    vertical_spacing=0.1,\n                    subplot_titles=('Adjusted Close Moving Average',\n                                    'Exponential Moving Average',\n                                    'Stock Return', 'Stock Volatility'))\n\nfor i, sector in enumerate(price_names.SectorName.unique()):\n    \n    sector_df=price_names[price_names.SectorName==sector]\n    periods=[0,10,30,50]\n    colors=px.colors.qualitative.Vivid\n    dash=['solid','dash', 'longdash', 'dashdot', 'longdashdot']\n    row,col=1,1\n    \n    for j, (feature, name) in enumerate(zip(features, names)):\n        if j>=2:\n            row,periods=2,[10,30,50]\n            colors=px.colors.qualitative.Bold[1:]\n        if j%2==0:\n            col=1\n        else:\n            col=2\n        \n        for k, period in enumerate(periods):\n            if (k==0)&(j<2):\n                plot_data=sector_df.groupby(sector_df.index)['AdjustedClose'].mean().rename('Adjusted Close')\n            elif j>=2:\n                plot_data=sector_df.groupby(sector_df.index)['{}_{}Day'.format(feature,period)].mean().mul(100).rename('{}-day {}'.format(period,name))\n            else:\n                plot_data=sector_df.groupby(sector_df.index)['{}_{}Day'.format(feature,period)].mean().rename('{}-day {}'.format(period,name))\n            fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data, mode='lines',\n                                     name=plot_data.name, marker_color=colors[k+1],\n                                     line=dict(width=2,dash=(dash[k] if j<2 else 'solid')), \n                                     showlegend=(True if (j==0) or (j==2) else False), legendgroup=row,\n                                     visible=(False if i != 0 else True)), row=row, col=col)\n            \n    visibility=[False]*14*len(price_names.SectorName.unique())\n    for l in range(i*14, i*14+14):\n        visibility[l]=True\n    button = dict(label = sector,\n                  method = \"update\",\n                  args=[{\"visible\": visibility}])\n    buttons.append(button)\n\nfig.update_layout(title='Stock Price Moving Average, Return,<br>and Volatility by Sector',\n                  template=temp, yaxis3_ticksuffix='%', yaxis4_ticksuffix='%',\n                  legend_title_text='Period', legend_tracegroupgap=250,\n                  updatemenus=[dict(active=0, type=\"dropdown\",\n                                    buttons=buttons, xanchor='left',\n                                    yanchor='bottom', y=1.105, x=.01)], \n                  hovermode='x unified', height=800,width=1200, margin=dict(t=150))\nfig.show()\n\n# %% [code] {\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T03:00:15.263099Z\",\"iopub.execute_input\":\"2023-08-01T03:00:15.263362Z\",\"iopub.status.idle\":\"2023-08-01T03:00:15.276450Z\",\"shell.execute_reply.started\":\"2023-08-01T03:00:15.263330Z\",\"shell.execute_reply\":\"2023-08-01T03:00:15.275359Z\"}}\ndef calc_spread_return_sharpe(df: pd.DataFrame, portfolio_size: int = 200, toprank_weight_ratio: float = 2) -> float:\n    \"\"\"\n    Args:\n        df (pd.DataFrame): predicted results\n        portfolio_size (int): # of equities to buy/sell\n        toprank_weight_ratio (float): the relative weight of the most highly ranked stock compared to the least.\n    Returns:\n        (float): sharpe ratio\n    \"\"\"\n    def _calc_spread_return_per_day(df, portfolio_size, toprank_weight_ratio):\n        \"\"\"\n        Args:\n            df (pd.DataFrame): predicted results\n            portfolio_size (int): # of equities to buy/sell\n            toprank_weight_ratio (float): the relative weight of the most highly ranked stock compared to the least.\n        Returns:\n            (float): spread return\n        \"\"\"\n        assert df['Rank'].min() == 0\n        assert df['Rank'].max() == len(df['Rank']) - 1\n        weights = np.linspace(start=toprank_weight_ratio, stop=1, num=portfolio_size)\n        purchase = (df.sort_values(by='Rank')['Target'][:portfolio_size] * weights).sum() / weights.mean()\n        short = (df.sort_values(by='Rank', ascending=False)['Target'][:portfolio_size] * weights).sum() / weights.mean()\n        return purchase - short\n\n    buf = df.groupby('Date').apply(_calc_spread_return_per_day, portfolio_size, toprank_weight_ratio)\n    sharpe_ratio = buf.mean() / buf.std()\n    return sharpe_ratio\n\n# %% [code] {\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T03:48:21.816068Z\",\"iopub.execute_input\":\"2023-08-01T03:48:21.816405Z\",\"iopub.status.idle\":\"2023-08-01T03:57:13.165339Z\",\"shell.execute_reply.started\":\"2023-08-01T03:48:21.816365Z\",\"shell.execute_reply\":\"2023-08-01T03:57:13.164259Z\"}}\nts_fold = TimeSeriesSplit(n_splits=10, gap=10000)\n#display(price_features.dropna().head(n=20))\nprices=price_features.dropna().sort_values(['Date','SecuritiesCode'])\ny=prices['Target'].to_numpy()\nX=prices.drop(['Target'],axis=1)\n#display(X.head(n=20))\n#display(y)\nfeat_importance=pd.DataFrame()\nsharpe_ratio=[]\n    \nfor fold, (train_idx, val_idx) in enumerate(ts_fold.split(X, y)):\n    \n    print(\"\\n========================== Fold {} ==========================\".format(fold+1))\n    X_train, y_train = X.iloc[train_idx,:], y[train_idx]\n    X_valid, y_val = X.iloc[val_idx,:], y[val_idx]\n    \n    print(\"Train Date range: {} to {}\".format(X_train.Date.min(),X_train.Date.max()))\n    print(\"Valid Date range: {} to {}\".format(X_valid.Date.min(),X_valid.Date.max()))\n    \n    X_train.drop(['Date','SecuritiesCode'], axis=1, inplace=True)\n    #display(X_valid.head(n=20))\n    X_val=X_valid[X_valid.columns[~X_valid.columns.isin(['Date','SecuritiesCode'])]]#时间序列的交叉验证，验证集一定发生在训练集后面。\n    val_dates=X_valid.Date.unique()[1:-1]#验证集应在每一天包含完整的所有股票，split时可能导致不完整，所以去掉验证集中最早和最晚的一天\n    #display(X_val.head(n=20))\n    #display(val_dates)\n    print(\"\\nTrain Shape: {} {}, Valid Shape: {} {}\".format(X_train.shape, y_train.shape, X_val.shape, y_val.shape))\n    \n    params = {'n_estimators': 500,\n              'num_leaves' : 100,\n              'learning_rate': 0.1,\n              'colsample_bytree': 0.9,\n              'subsample': 0.8,\n              'reg_alpha': 0.4,\n              'metric': 'mae',\n              'random_state': 21}\n    \n    gbm = LGBMRegressor(**params).fit(X_train, y_train, \n                                      eval_set=[(X_train, y_train), (X_val, y_val)],\n                                      verbose=300, \n                                      eval_metric=['mae','mse'])\n    y_pred = gbm.predict(X_val)\n    rmse = np.sqrt(mean_squared_error(y_val, y_pred))\n    mae = mean_absolute_error(y_val, y_pred)\n    feat_importance[\"Importance_Fold\"+str(fold)]=gbm.feature_importances_\n    feat_importance.set_index(X_train.columns, inplace=True)\n    \n    rank=[]\n    X_val_df=X_valid[X_valid.Date.isin(val_dates)]\n    #display(X_val_df.head(n=20))\n    for i in X_val_df.Date.unique():#在验证集每一天按《预测值》排序rank\n        temp_df = X_val_df[X_val_df.Date == i].drop(['Date','SecuritiesCode'],axis=1)\n        temp_df[\"pred\"] = gbm.predict(temp_df)\n        temp_df[\"Rank\"] = (temp_df[\"pred\"].rank(method=\"first\", ascending=False)-1).astype(int)\n        rank.append(temp_df[\"Rank\"].values)\n\n    stock_rank=pd.Series([x for y in rank for x in y], name=\"Rank\")\n    df=pd.concat([X_val_df.reset_index(drop=True),stock_rank,\n                  prices[prices.Date.isin(val_dates)]['Target'].reset_index(drop=True)], axis=1)\n    #display(df.head(n=20))\n    sharpe=calc_spread_return_sharpe(df)\n    sharpe_ratio.append(sharpe)\n    print(\"Valid Sharpe: {}, RMSE: {}, MAE: {}\".format(sharpe,rmse,mae))\n    \n    del X_train, y_train,  X_val, y_val\n    gc.collect()\n    \nprint(\"\\nAverage cross-validation Sharpe Ratio: {:.4f}, standard deviation = {:.2f}.\".format(np.mean(sharpe_ratio),np.std(sharpe_ratio)))\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T03:57:17.942686Z\",\"iopub.execute_input\":\"2023-08-01T03:57:17.943029Z\",\"iopub.status.idle\":\"2023-08-01T03:57:18.162274Z\",\"shell.execute_reply.started\":\"2023-08-01T03:57:17.942991Z\",\"shell.execute_reply\":\"2023-08-01T03:57:18.161458Z\"}}\nfeat_importance['avg'] = feat_importance.mean(axis=1)\nfeat_importance = feat_importance.sort_values(by='avg',ascending=True)\npal=sns.color_palette(\"plasma_r\", 29).as_hex()[2:]\n\nfig=go.Figure()\nfor i in range(len(feat_importance.index)):\n    fig.add_shape(dict(type=\"line\", y0=i, y1=i, x0=0, x1=feat_importance['avg'][i], \n                       line_color=pal[::-1][i],opacity=0.7,line_width=4))\nfig.add_trace(go.Scatter(x=feat_importance['avg'], y=feat_importance.index, mode='markers', \n                         marker_color=pal[::-1], marker_size=8,\n                         hovertemplate='%{y} Importance = %{x:.0f}<extra></extra>'))\nfig.update_layout(template=temp,title='Overall Feature Importance', \n                  xaxis=dict(title='Average Importance',zeroline=False),\n                  yaxis_showgrid=False, margin=dict(l=120,t=80),\n                  height=700, width=800)\nfig.show()\n\n# %% [code] {\"_kg_hide-input\":true,\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T03:57:59.051361Z\",\"iopub.execute_input\":\"2023-08-01T03:57:59.051669Z\",\"iopub.status.idle\":\"2023-08-01T03:58:51.745242Z\",\"shell.execute_reply.started\":\"2023-08-01T03:57:59.051634Z\",\"shell.execute_reply\":\"2023-08-01T03:58:51.744545Z\"}}\ncols_fin=feat_importance.avg.nlargest(11).index.tolist()\ncols_fin.extend(('Open','High','Low'))\ndisplay(prices.head(n=20))\nX_train=prices[cols_fin]\ny_train=prices['Target']\ngbm = LGBMRegressor(**params).fit(X_train, y_train)\n\n# %% [code] {\"jupyter\":{\"outputs_hidden\":false},\"execution\":{\"iopub.status.busy\":\"2023-08-01T03:59:04.996704Z\",\"iopub.execute_input\":\"2023-08-01T03:59:04.997037Z\",\"iopub.status.idle\":\"2023-08-01T03:59:35.506736Z\",\"shell.execute_reply.started\":\"2023-08-01T03:59:04.997001Z\",\"shell.execute_reply\":\"2023-08-01T03:59:35.505938Z\"}}\nimport jpx_tokyo_market_prediction\njpx_tokyo_market_prediction.make_env.__called__ = False\nenv = jpx_tokyo_market_prediction.make_env()\niter_test = env.iter_test()\n\n#display(train.head(n=20))\n\ncols=['Date','SecuritiesCode','Open','High','Low','Close','Volume','AdjustmentFactor']\ntrain=train[train.Date>='2021-08-01'][cols]\n\ncounter = 0\nfor (prices, options, financials, trades, secondary_prices, sample_prediction) in iter_test:\n\n    current_date = prices[\"Date\"].iloc[0]\n    display(current_date)\n    if counter == 0:\n        df_price_raw = train.loc[train[\"Date\"] < current_date]\n    df_price_raw = pd.concat([df_price_raw, prices[cols]]).reset_index(drop=True)\n    df_price = adjust_price(df_price_raw)\n    features = create_features(df=df_price)\n    display(features.head(n=90))\n    feat = features[features.Date == current_date][cols_fin]\n    feat[\"pred\"] = gbm.predict(feat)\n    feat[\"Rank\"] = (feat[\"pred\"].rank(method=\"first\", ascending=False)-1).astype(int)\n    sample_prediction[\"Rank\"] = feat[\"Rank\"].values\n    display(sample_prediction.head())\n    \n    assert sample_prediction[\"Rank\"].notna().all()\n    assert sample_prediction[\"Rank\"].min() == 0\n    assert sample_prediction[\"Rank\"].max() == len(sample_prediction[\"Rank\"]) - 1\n    \n    env.predict(sample_prediction)\n    counter += 1","metadata":{"_uuid":"0d7cd4fa-58ec-43d4-8483-41b905e49d4f","_cell_guid":"8509ffcc-7e6e-430b-9ad2-78f5ce7cce45","collapsed":false,"jupyter":{"outputs_hidden":false},"trusted":true},"execution_count":null,"outputs":[]}]}