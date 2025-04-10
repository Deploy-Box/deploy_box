def gcp_id_extractor(service_id: str, option="frontend") -> str:
    valid_options = ["frontend", "backend"]

    if option not in valid_options:
        raise ValueError(
            f"Invalid option '{option}'. Choose from {valid_options} default is 'frontend' if no arg given."
        )

    if option == "frontend":
        prefix = "frontend-"
    else:
        prefix = "backend-"

    return service_id.removeprefix(prefix)
