if __name__ == '__main__':
    import sys
    if '--self-test' in sys.argv:
        from office_tools.self_test import run
        run(sys.argv[sys.argv.index('--self-test') + 1])
    else:
        from office_tools.app import main
        main()
