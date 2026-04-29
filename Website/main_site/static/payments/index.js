// Global variables
let stripe;
let currentOrganizationId = null;

// Get Stripe publishable key
fetch("/api/v1/payments/config")
  .then((result) => {
    return result.json();
  })
  .then((data) => {
    // Initialize Stripe.js
    stripe = Stripe(data.public_key);

    // Event handler
    document.querySelectorAll("#submitBtn").forEach((button) => {
      button.addEventListener("click", async () => {
        const stack_id = button.getAttribute("data-stack-id");
        const org_id = document.getElementById("org_dropdown").value;
        const project_id = document.getElementById("project_dropdown").value;

        // Validate selections
        if (!org_id) {
          showToast("Please select an organization before purchasing", "warning");
          return;
        }
        if (!project_id) {
          showToast("Please select a project before purchasing", "warning");
          return;
        }

        // Get Checkout Session ID
        fetch(`/api/v1/payments/checkout/create/${org_id}/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ stack_id: stack_id, project_id: project_id }),
        })
          .then((result) => {
            return result.json();
          })
          .then((data) => {
            if (data.error) {
              // Show error message to user
              showToast(data.error, "error");
              return;
            }
            console.log("sessionID", data);
            // Redirect to Stripe Checkout
            return stripe.redirectToCheckout({ sessionId: data.sessionId });
          })
          .then((res) => {
            if (res && res.error) {
              console.error("Stripe checkout error:", res.error);
              showToast("Error redirecting to payment page. Please try again.", "error");
            }
          })
          .catch((error) => {
            console.error("Error creating checkout session:", error);
            showToast("Failed to create checkout session. Please try again.", "error");
          });
      });
    });
  });

const org_dropdown = document.getElementById("org_dropdown");

org_dropdown.addEventListener("change", () => {
  const org_id = org_dropdown.value;
  console.log(org_id);

  let project_options = document.querySelectorAll("#project_dropdown option");

  project_options.forEach((option) => {
    console.log(option.getAttribute("org_id"));
    console.log(org_id);

    if (option.getAttribute("org_id") !== org_id) {
      option.style.display = "none";
    } else {
      option.style.display = "block";
    }
  });

  // Reset project dropdown to default placeholder when organization changes
  document.getElementById("project_dropdown").value = "";
});
