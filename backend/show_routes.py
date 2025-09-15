from app import app

if __name__ == '__main__':
    print("\n注册的路由列表：")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.methods} {rule}")
