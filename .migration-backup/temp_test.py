from pydantic import BaseModel, root_validator
from typing import Optional

class M(BaseModel):
    message: Optional[str] = None
    input: Optional[str] = None

    @root_validator(pre=True)
    def check(cls, values):
        print('root validator receives', values)
        msg = values.get('message')
        if not msg and 'input' in values:
            msg = values.get('input')
        if not msg:
            raise ValueError('need message or input')
        values['message'] = msg
        return values

print('create empty')
try:
    print(M())
except Exception as e:
    print('error', e)

print('create with message')
print(M(message='hello'))

print('create with input')
print(M(input='hi'))

print('create with both')
print(M(message='hey', input='ignored'))
