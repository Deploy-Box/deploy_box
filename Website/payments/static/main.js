console.log("Sanity check2!");

// Get Stripe publishable key
fetch("/api/payments/config")
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
        console.log(stackId);

        // Get Checkout Session ID
        fetch('/api/payments/create-checkout-session/', {
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
            console.log(data);
            // Redirect to Stripe Checkout
            return stripe.redirectToCheckout({ sessionId: data.sessionId });
          })
          .then((res) => {
            console.log(res);
          });
      });
    });
  });
