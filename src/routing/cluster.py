import random


class ConnectedCluster:
    def __init__(self):
        self.cluster_id = random.randint(1, 1000000)

        self.points = set()

    def add_point(self, point) -> None:
        self.points.add(point)

    def add_points(self, points) -> None:
        self.points.update(points)

    def merge(self, other_cluster) -> None:
        self.points.update(other_cluster.points)

    def __str__(self):
        return f"Cluster {self.cluster_id} ({len(self.points)} points)"


class ClusterManager:
    def __init__(self):
        self.clusters = []

    def find_cluster_id_for_point(self, point):
        for idx, cluster in enumerate(self.clusters):
            if point in cluster.points:
                return idx
        return -1

    def add_point_to_cluster(self, point) -> None:
        if self.find_cluster_id_for_point(point) != -1:
            return  # Point already belongs to a cluster
        new_cluster = ConnectedCluster()
        new_cluster.add_point(point)
        self.clusters.append(new_cluster)

    def add_points_to_cluster(self, points) -> None:
        if len(points) == 0:
            return
        first_point = points[0]
        cluster_id = self.find_cluster_id_for_point(first_point)
        if cluster_id == -1:
            new_cluster = ConnectedCluster()
            new_cluster.add_points(points)
            self.clusters.append(new_cluster)
        else:
            self.clusters[cluster_id].add_points(points)
        self.auto_merge_clusters()

    def auto_merge_clusters(self) -> None:
        # new_clusters = []
        for c in self.clusters:
            for d in self.clusters:
                if c != d and any(p in d.points for p in c.points):
                    c.merge(d)
                    self.clusters.remove(d)

    def get_cluster_for_point(self, point):
        for cluster in self.clusters:
            if point in cluster.points:
                return cluster
        return None

    def add_cluster(self, cluster: ConnectedCluster) -> None:
        self.clusters.append(cluster)

    def merge_clusters(
        self, cluster1: ConnectedCluster, cluster2: ConnectedCluster
    ) -> None:
        cluster1.merge(cluster2)
        self.clusters.remove(cluster2)

    def get_clusters(self):
        return self.clusters

    def __len__(self):
        return len(self.clusters)
