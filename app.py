@app.route("/subscribe", methods=["GET"])
def subscribe():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": "price_xxx12345",  # Replace with your Stripe Price ID
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=url_for("subscription_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("home", _external=True),
        )
        return jsonify({"checkout_url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
