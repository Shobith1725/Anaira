import os
import sys
from dotenv import load_dotenv

load_dotenv()
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    print('Missing URL or KEY')
    sys.exit(1)

try:
    from supabase import create_client, Client
    supabase: Client = create_client(supabase_url, supabase_key)
    res = supabase.table('drivers').select('*').limit(1).execute()
    print('Supabase connection successful!')
    print(res.data)
except Exception as e:
    print(f'Error connecting to Supabase: {e}')
