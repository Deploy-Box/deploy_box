console.log("Sanity check2!");

// Get Stripe publishable key
fetch("/api/v1/payments/config")
  .then((result) => {
    return result.json();
  })
  .then((data) => {
    // Initialize Stripe.js
    const stripe = Stripe(data.publicKey);

    // Event handler
    document.querySelectorAll("#submitBtn").forEach((button) => {
      button.addEventListener("click", () => {
        const stackId = button.getAttribute("data-stack-id");
        const org_id = document.getElementById("org_choice").value;
        console.log(stackId);

        // Get Checkout Session ID
        fetch(`/api/v1/payments/checkout/create/${org_id}/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ stackId: stackId }),
        })
          .then((result) => {
            return result.json();
          })
          .then((data) => {
            console.log("sessionID", data);
            // Redirect to Stripe Checkout
            return stripe.redirectToCheckout({ sessionId: data.sessionId });
          })
          .then((res) => {
            console.log(res);
          });
      });
    });
  });
