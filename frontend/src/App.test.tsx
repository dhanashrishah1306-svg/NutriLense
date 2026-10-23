import {describe,it,expect,vi} from 'vitest'; import {render,screen} from '@testing-library/react'; import App from './App';
vi.mock('./lib/api',()=>({health:()=>Promise.resolve({status:'ok'}),uploadImage:vi.fn(),analyze:vi.fn(),nutrition:vi.fn()}));
describe('NutriLens shell',()=>{it('renders dashboard and scan call to action',()=>{render(<App/>);expect(screen.getByText(/Scan food/i)).toBeInTheDocument();expect(screen.getByRole('button',{name:/Start a new scan/i})).toBeInTheDocument()})});
