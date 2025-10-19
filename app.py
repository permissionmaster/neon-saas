from flask import Flask, render_template, request, redirect, url_for
import stripe, json, boto3, os

app=Flask(__name__)
stripe.api_key=os.getenv("STRIPE_KEY","sk_test_***")
PK_KEY=os.getenv("STRIPE_PK","pk_test_***")

@app.route("/")
def index():
    return render_template("index.html", pk=PK_KEY)

@app.route("/pay", methods=["POST"])
def pay():
    # 고객 생성 → 결제 링크
    cust=stripe.Customer.create(email=request.form["email"], name=request.form["name"])
    price=os.getenv("PRICE_ID","price_1M***")  # Stripe 대시보서 만든 Price
    sess=stripe.checkout.Session.create(
        customer=cust.id,
        payment_method_types=["card"],
        line_items=[{"price":price, "quantity":1}],
        mode="subscription",
        success_url=request.host_url+url_for("success", cid=cust.id),
        cancel_url=request.host_url)
    return redirect(sess.url, code=303)

@app.route("/success")
def success():
    cid=request.args.get("cid")
    # 인프라 생성
    import provision
    info=provision.run()
    return render_template("customer.html", cid=cid, info=info)

@app.route("/admin")
def admin():
    # Athena 비용 조회 (profit.py 결과)
    try:
        with open("profit.json") as f:
            pf=json.load(f)
    except:
        pf={"revenue":0, "cost":0, "profit":0}
    return render_template("admin.html", pf=pf)

if __name__=="__main__":
    app.run(debug=True)
