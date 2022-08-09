import { Navbar } from '../components/Navbar.jsx'

const Home = () => {
    return (
        <div class="w-full bg-[#0D1117]">
            <Navbar />
            <div class="w-4/5 h-screen mx-auto mt-5">
                <h1 class="text-4xl text-white font-semibold mb-20">
                    Home
                </h1>

            </div>
        </div>
    );
}

export { Home };