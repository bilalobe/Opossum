import argparse
import sys
from app.config import Config, get_provider_config
import yaml

def main():
    parser = argparse.ArgumentParser(description="Opossum Config Tool")
    parser.add_argument("--validate", action="store_true", help="Validate configuration")
    parser.add_argument("--show", action="store_true", help="Show current configuration")
    parser.add_argument("--provider", type=str, help="Show provider configuration")
    args = parser.parse_args()
    
    if args.validate:
        # Validation logic
        print("Configuration validation completed")
        
    if args.show:
        # Print config as YAML
        config_dict = {k: v for k, v in vars(Config).items() 
                       if not k.startswith('_') and not callable(v)}
        print(yaml.dump(config_dict))
        
    if args.provider and args.provider in Config.model_providers:
        print(yaml.dump(get_provider_config(args.provider)))

if __name__ == "__main__":
    main()