

class ServiceHelper:
    def find_nested_value(self, obj, target_key):
        """
        Recursively searches for the target_key in a nested dictionary or list,
        and returns its value if found.
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == target_key:
                    return value
                result = self.find_nested_value(value, target_key)
                if result is not None:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = self.find_nested_value(item, target_key)
                if result is not None:
                    return result
        return None

    def update_nested_value(self, obj, target_key, new_value):
        """
        Recursively searches for the target_key in a nested dictionary or list,
        and updates its value to new_value.
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == target_key:
                    obj[key] = new_value
                else:
                    self.update_nested_value(value, target_key, new_value)
        elif isinstance(obj, list):
            for item in obj:
                self.update_nested_value(item, target_key, new_value)