class ExtraFlags:

    # Flags the plugin actually acts on (boto3 push/pull only honor these).
    SUPPORTED = ('dryrun', 'dry-run', 'delete', 'force')

    @staticmethod
    def _normalize(flag):
        return flag[2:] if flag.startswith('--') else flag

    @classmethod
    def convert(kls, raw_flags):
        return [f"--{kls._normalize(flag)}" for flag in raw_flags]

    @classmethod
    def unsupported(kls, raw_flags):
        return [flag for flag in raw_flags if kls._normalize(flag) not in kls.SUPPORTED]
