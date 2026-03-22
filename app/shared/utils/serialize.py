def orm_to_dict(instance: object) -> dict:
    return {
        key: value
        for key, value in instance.__dict__.items()
        if not key.startswith("_sa_")
    }
