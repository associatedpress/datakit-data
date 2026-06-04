class ExtraFlags:

    @classmethod
    def convert(kls, raw_flags):
        return [f"--{flag}" for flag in raw_flags]
