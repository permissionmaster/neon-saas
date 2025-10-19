import boto3, json, stripe, os
from datetime import datetime, timedelta
ce=boto3.client("ce"); sts=boto3.client("sts")
stripe.api_key=os.getenv("STRIPE_KEY")

def daily():
    today=datetime.today()
    yest=(today-timedelta(1)).strftime("%Y-%m-%d")
    # AWS cost
    cost=float(ce.get_cost_and_usage(
        TimePeriod={"Start":yest,"End":today.strftime("%Y-%m-%d")},
        Granularity="DAILY", Metrics=["BlendedCost"],
        Filter={"Tags":{"Key":"Project","Values":["neon"]}}
    )["ResultsByTime"][0]["Total"]["BlendedCost"]["Amount"])
    # Stripe revenue
    rev=sum([ch["amount"]/100 for ch in stripe.Charge.list(created={
        "gte":int((today-timedelta(1)).timestamp()),
        "lt":int(today.timestamp())
    }).auto_paging_iter()])
    profit=rev-cost
    with open("profit.json","w") as f:
        json.dump({"revenue":rev,"cost":cost,"profit":profit}, f)

if __name__=="__main__":
    daily()
