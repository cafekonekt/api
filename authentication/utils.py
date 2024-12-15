class RoleBasedSerializer:
    def __init__(self, role_serializer_map):
        self.role_serializer_map = role_serializer_map

    def get_serializer_class(self, role):
        return self.role_serializer_map.get(role, None)
