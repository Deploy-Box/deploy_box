document.getElementById("deleteOrgBtn").addEventListener("click", function () {
  if (
    confirm(
      "Are you sure you want to delete this organization? This action cannot be undone."
    )
  ) {
    const organizationId = document.getElementById("deleteOrgBtn").value;
    fetch(`/api/v1/organizations/${organizationId}/`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then((response) => {
        if (response.ok) {
          window.location.href = "/dashboard/"; // Redirect to organizations list
        } else {
          throw new Error("Failed to delete organization");
        }
      })
      .catch((error) => {
        console.error("Error deleting organization:", error);
        alert("Failed to delete organization. Please try again.");
      });
  }
});
