class ExtraFlags:

    # Flags the plugin actually acts on (boto3 push/pull only honor these).
    SUPPORTED = ('dryrun', 'dry-run', 'delete')

    @classmethod
    def convert(kls, raw_flags):
        return [f"--{flag}" for flag in raw_flags]

    @classmethod
    def unsupported(kls, raw_flags):
        return [flag for flag in raw_flags if flag not in kls.SUPPORTED]
