import os


class SyncMarkers:
    """Bookkeeping for per-file sync markers under a sync status directory.

    For each data file `foo.csv`, a marker `foo.csv.synced` mirrors its path under the
    sync status directory. The marker's content is the object's S3 ETag at sync time
    (the basis for detecting remote changes); its mtime is the sync time (the basis for
    detecting local changes — a file is stale when its mtime is strictly newer than its
    marker's).

    A falsy sync_status_dir disables bookkeeping: reads report no record and `enabled`
    is False. Callers must check `enabled` before calling `write`.
    """

    SUFFIX = '.synced'

    def __init__(self, sync_status_dir):
        self.sync_status_dir = sync_status_dir

    @property
    def enabled(self):
        return bool(self.sync_status_dir)

    def read(self, rel_path):
        """Return the (etag, mtime) recorded for rel_path. The etag is None when there is
        no usable record (no location configured, no marker, or a legacy/empty marker);
        the mtime is None only when the marker itself is missing."""
        marker_path = self._path(rel_path)
        if marker_path is None or not os.path.exists(marker_path):
            return None, None
        with open(marker_path) as f:
            etag = f.read().strip()
        return etag or None, os.path.getmtime(marker_path)

    def etag(self, rel_path):
        return self.read(rel_path)[0]

    def is_fresh(self, rel_path, local_path):
        """True when a marker exists and is at least as new as the data file, i.e. the
        file has not been modified on disk since the last sync."""
        _, marker_mtime = self.read(rel_path)
        return marker_mtime is not None and marker_mtime >= os.path.getmtime(local_path)

    def write(self, rel_path, etag):
        marker_path = self._path(rel_path)
        os.makedirs(os.path.dirname(os.path.abspath(marker_path)), exist_ok=True)
        with open(marker_path, 'w') as f:
            f.write(etag or '')

    def latest_mtime(self):
        """The mtime of the most recently written marker, or None when there are none."""
        if not self.enabled or not os.path.isdir(self.sync_status_dir):
            return None
        mtimes = [
            os.path.getmtime(os.path.join(root, filename))
            for root, _, filenames in os.walk(self.sync_status_dir)
            for filename in filenames
            if filename.endswith(self.SUFFIX)
        ]
        return max(mtimes, default=None)

    def _path(self, rel_path):
        if not self.enabled:
            return None
        return os.path.join(self.sync_status_dir, rel_path + self.SUFFIX)
